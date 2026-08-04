import os
import base64
import json

from typing import List, Dict, Any

class HtmlGenerator:
    """
    Generates an interactive HTML file with synchronized audio and highlighted text.
    The output HTML is fully portable, with embedded Base64 audio and offline-ready JS/CSS.
    """
    
    def __init__(self, text: str, word_boundaries: List[Dict[str, Any]], audio_path: str, output_path: str, speed: float = 1.0) -> None:
        """
        Initializes the HtmlGenerator.
        
        Args:
            text (str): The original markdown text.
            word_boundaries (List[Dict[str, Any]]): List of word boundary dictionaries containing offset, duration, and text.
            audio_path (str): Path to the temporary combined audio file.
            output_path (str): Path where the final HTML file will be saved.
            speed (float): The playback speed to be set initially in the HTML player.
        """
        self.text = text
        self.word_boundaries = word_boundaries
        self.audio_path = audio_path
        self.output_path = os.path.abspath(output_path)
        self.speed = speed

    def generate(self) -> None:
        """
        Processes the text and word boundaries to generate the interactive HTML file.
        Aligns TTS timestamps with the original markdown text and injects highlights.
        """
        # 1. 単語のアライメント（テキスト内の位置を特定）
        aligned = []
        search_start = 0
        for wb in self.word_boundaries:
            word = wb['text']
            idx = self.text.find(word, search_start)
            
            if idx != -1:
                jump = idx - search_start
                is_safe_jump = True
                
                # 安全なジャンプ（本来のテキストストリーム上でのマッチ）であるかを検証
                # TTSの読み上げによる単語の変化（「1」→「いち」等）で、
                # 全く関係ない後ろのテキストに誤爆してジャンプしてしまうのを防ぐ
                if jump > 15:
                    if jump > 1000 and len(word) <= 4:
                        is_safe_jump = False
                    elif jump > 200 and len(word) <= 3:
                        is_safe_jump = False
                    elif jump > 50 and len(word) <= 2:
                        is_safe_jump = False
                    elif jump > 15 and len(word) <= 1:
                        is_safe_jump = False
                
                if not is_safe_jump:
                    idx = -1
            
            if idx != -1:
                aligned.append((idx, idx + len(word), wb))
                search_start = idx + len(word)
                
        # 2. HTMLの<span>タグの代わりに、一意のプレースホルダーをMarkdownに埋め込む
        # （バッククォート内などでHTMLエスケープされるのを防ぐため）
        marked_text = self.text
        span_data = {}
        # 後ろから置換することでインデックスのズレを防ぐ
        for i, (start, end, wb) in reversed(list(enumerate(aligned))):
            word = marked_text[start:end]
            start_sec = wb['offset'] / 10_000_000.0
            end_sec = (wb['offset'] + wb['duration']) / 10_000_000.0
            
            span_data[i] = {
                "start": start_sec,
                "end": end_sec
            }
            placeholder_start = f"@@@HL_START_{i}@@@"
            placeholder_end = f"@@@HL_END_{i}@@@"
            marked_text = marked_text[:start] + placeholder_start + word + placeholder_end + marked_text[end:]
            
        # 3. 音声ファイルをBase64エンコードして完全ポータブルにする
        with open(self.audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            
        # 4. HTMLの生成
        html_content = self._get_html_template(marked_text, audio_b64, span_data)
        
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _get_html_template(self, markdown_text: str, audio_b64: str, span_data: Dict[int, Dict[str, float]]) -> str:
        """
        Constructs the final HTML string using the provided marked down text, base64 audio, and timing data.
        
        Args:
            markdown_text (str): The markdown text with injected highlight placeholders.
            audio_b64 (str): The Base64 encoded string of the audio file.
            span_data (Dict[int, Dict[str, float]]): Mapping of placeholder IDs to start/end times in seconds.
            
        Returns:
            str: The complete HTML content.
        """
        # JSのテンプレートリテラルに埋め込むためのエスケープ処理
        safe_markdown = markdown_text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        safe_markdown = safe_markdown.replace("\n", "\\n")
        
        span_data_json = json.dumps(span_data)
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Interactive Markdown Player</title>
<!-- Marked.js for Markdown parsing -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<!-- Mermaid.js for diagrams -->
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<style>
    :root {{
        --bg-color: #ffffff;
        --text-color: #37352f;
        --hl-color: rgba(255, 212, 0, 0.4);
        --callout-bg: #f1f1ef;
        --callout-border: transparent;
        --code-bg: #f7f6f3;
        --code-color: #eb5757;
        --border-color: #e9e9e7;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol";
        background-color: var(--bg-color);
        color: var(--text-color);
        line-height: 1.6;
        padding: 60px 40px;
        max-width: 800px;
        margin: 0 auto;
        font-size: 17px;
        padding-bottom: 50vh; /* Allow scrolling past the end */
    }}
    
    /* Player Controls (Commercial Notion-like Design) */
    #player-container {{
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 650px;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(0, 0, 0, 0.08);
        padding: 12px 24px;
        border-radius: 100px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1), 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 15px;
        z-index: 1000;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }}
    
    audio {{
        flex-grow: 1;
        height: 40px;
        outline: none;
    }}
    
    .speed-control {{
        font-weight: 600;
        background: transparent;
        border: none;
        padding: 8px 12px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 14px;
        color: #555;
        outline: none;
        transition: background 0.2s;
    }}
    .speed-control:hover {{
        background: rgba(0,0,0,0.05);
    }}

    /* Markdown Styles (Notion-like) */
    h1, h2, h3, h4 {{
        color: var(--text-color);
        font-weight: 700;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        line-height: 1.2;
    }}
    h1 {{ font-size: 40px; margin-top: 2em; margin-bottom: 0.5em; }}
    h2 {{ font-size: 30px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px; }}
    h3 {{ font-size: 24px; }}
    h4 {{ font-size: 20px; }}
    
    p {{ margin-top: 0.2em; margin-bottom: 0.2em; min-height: 1.2em; }}
    
    ul, ol {{
        margin-top: 0.2em;
        margin-bottom: 0.2em;
        padding-left: 24px;
    }}
    li {{
        margin-top: 0.2em;
        margin-bottom: 0.2em;
    }}
    li > aside, li > blockquote, li > p, li > div, li > table, li > ul, li > ol {{
        margin-top: 0.5em;
        margin-bottom: 0.5em;
    }}
    
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 1.5em 0;
        font-size: 0.9em;
    }}
    th, td {{
        border: 1px solid var(--border-color);
        padding: 8px 12px;
        text-align: left;
    }}
    th {{
        background-color: var(--code-bg);
        font-weight: 600;
    }}
    
    aside, blockquote {{
        background-color: var(--callout-bg);
        border: 1px solid var(--callout-border);
        border-radius: 4px;
        padding: 16px 20px;
        margin: 1em 0;
        display: flex;
        flex-direction: column;
    }}
    blockquote {{
        border-left: 3px solid #37352f;
        background-color: transparent;
        padding-left: 14px;
        margin-left: 0;
    }}
    
    code {{
        background-color: var(--code-bg);
        color: var(--code-color);
        padding: 0.2em 0.4em;
        border-radius: 3px;
        font-size: 0.85em;
        font-family: Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace;
    }}
    pre code {{
        display: block;
        padding: 1em;
        overflow-x: auto;
        color: #333;
        background-color: var(--code-bg);
    }}
    
    /* Mermaid diagram container */
    .mermaid {{
        margin: 2em 0;
        display: flex;
        justify-content: center;
    }}
    
    /* Highlight Style */
    .hl-word {{
        transition: background-color 0.1s, transform 0.1s;
        border-radius: 2px;
        cursor: pointer;
    }}
    .hl-word:hover {{
        background-color: rgba(255, 212, 0, 0.2);
    }}
    .hl-word.active {{
        background-color: var(--hl-color);
        font-weight: 600;
        box-shadow: 0 0 0 2px var(--hl-color);
    }}
    
    hr {{
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 2em 0;
    }}
</style>
</head>
<body>

<div id="content"></div>

<div id="player-container">
    <audio id="audio-player" controls autoplay>
        <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        Your browser does not support the audio element.
    </audio>
    <select id="speed-select" class="speed-control">
        <option value="1.0">1.0x</option>
        <option value="1.5">1.5x</option>
        <option value="2.0">2.0x</option>
        <option value="2.5">2.5x</option>
        <option value="3.0">3.0x</option>
    </select>
</div>

<script>
    // Marked.js options: enable line breaks
    marked.setOptions({{ breaks: true }});

    // 1. MarkdownをHTMLに変換
    let markdownText = `{safe_markdown}`;
    let html = marked.parse(markdownText);
    
    // 2. プレースホルダーを実際のSPANタグに置換 (マークダウン変換後に行うことでコードブロック内の崩れを防ぐ)
    const spanData = {span_data_json};
    
    html = html.replace(/@@@HL_START_(\d+)@@@/g, (match, id) => {{
        const data = spanData[id];
        return `<span class="hl-word" id="w${{id}}" data-start="${{data.start}}" data-end="${{data.end}}">`;
    }});
    html = html.replace(/@@@HL_END_(\d+)@@@/g, "</span>");
    
    // HTMLの崩れを修正 (タグの間に不要な <p> が入るのを防ぐ)
    html = html.replace(/<p><span class="hl-word"/g, '<span class="hl-word"');
    html = html.replace(/<\/span><\/p>/g, '</span>');
    html = html.replace(/<p><\/span>/g, '</span>');
    
    document.getElementById('content').innerHTML = html;
    
    // 3. Mermaid記法の描画
    mermaid.initialize({{ startOnLoad: false, theme: 'default' }});
    setTimeout(() => {{
        const mermaidBlocks = document.querySelectorAll('code.language-mermaid');
        mermaidBlocks.forEach((block) => {{
            const div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = block.textContent;
            // プレースホルダーから置換されたspanがmermaidコードブロック内に混入している場合はテキストに戻す
            div.textContent = div.textContent.replace(/<span[^>]*>/g, '').replace(/<\\/span>/g, '');
            block.parentNode.replaceWith(div);
        }});
        if (mermaidBlocks.length > 0) {{
            mermaid.run();
        }}
    }}, 0);
    
    // 4. 音声プレイヤーとハイライトの制御
    const audio = document.getElementById('audio-player');
    const speedSelect = document.getElementById('speed-select');
    const words = Array.from(document.querySelectorAll('.hl-word'));
    
    // 5. テキストクリックでそこから再生する機能
    words.forEach(word => {{
        word.addEventListener('click', () => {{
            audio.currentTime = parseFloat(word.dataset.start);
            audio.play();
        }});
    }});

    // 初期倍速の設定
    const initialSpeed = {self.speed};
    audio.playbackRate = initialSpeed;
    
    // Selectボックスの初期値合わせ
    const validSpeeds = [1.0, 1.5, 2.0, 2.5, 3.0];
    let closestSpeed = validSpeeds.reduce((prev, curr) => Math.abs(curr - initialSpeed) < Math.abs(prev - initialSpeed) ? curr : prev);
    speedSelect.value = closestSpeed.toFixed(1);
    
    speedSelect.addEventListener('change', (e) => {{
        audio.playbackRate = parseFloat(e.target.value);
    }});
    
    let activeWordIndex = -1;
    let isScrolling = false;
    
    audio.addEventListener('seeked', () => {{
        isScrolling = false; // シーク時はスクロールロックを解除
    }});
    
    audio.addEventListener('timeupdate', () => {{
        const currentTime = audio.currentTime;
        
        let foundIndex = -1;
        // 現在時刻に該当する、もしくは現在時刻の直前の単語を探す
        for (let i = 0; i < words.length; i++) {{
            const start = parseFloat(words[i].dataset.start);
            const end = parseFloat(words[i].dataset.end);
            if (currentTime >= start && currentTime <= end) {{
                foundIndex = i;
                break;
            }} else if (start > currentTime) {{
                // 通り過ぎたので、直前の単語を現在のアクティブとする
                foundIndex = i > 0 ? i - 1 : 0;
                break;
            }}
        }}
        // もし最後まで見つからなかったら最後の単語
        if (foundIndex === -1 && words.length > 0) {{
            foundIndex = words.length - 1;
        }}
        
        if (foundIndex !== -1 && foundIndex !== activeWordIndex) {{
            if (activeWordIndex !== -1 && words[activeWordIndex]) {{
                words[activeWordIndex].classList.remove('active');
            }}
            
            words[foundIndex].classList.add('active');
            activeWordIndex = foundIndex;
            
            // 自動スクロール処理 (見切れ防止)
            const wordEl = words[foundIndex];
            const rect = wordEl.getBoundingClientRect();
            const viewHeight = window.innerHeight;
            
            // 画面の中央40%から外れたらスクロールする
            if (rect.top < viewHeight * 0.3 || rect.bottom > viewHeight * 0.7) {{
                if (!isScrolling) {{
                    wordEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    isScrolling = true;
                    // スクロールアニメーションの完了を待機
                    setTimeout(() => {{ isScrolling = false; }}, 400);
                }}
            }}
        }}
    }});
    
    audio.addEventListener('ended', () => {{
        if (activeWordIndex !== -1 && words[activeWordIndex]) {{
            words[activeWordIndex].classList.remove('active');
            activeWordIndex = -1;
        }}
    }});
</script>

</body>
</html>
"""
