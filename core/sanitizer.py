import os
import sys
import json
import re
from typing import Dict, Any, Optional
from core.logger import UILogger

class TextSanitizer:
    """
    Handles loading of sanitization rules from configuration and 
    processing text accordingly.
    """
    def __init__(self, logger: Optional[UILogger] = None):
        self.logger = logger
        self.sanitize_rules: Dict[str, Any] = self._get_default_rules()
        self.rules_path: str = self._get_rules_path()

    def _get_rules_path(self) -> str:
        """Determines the correct path for the rules configuration file."""
        if getattr(sys, 'frozen', False):
            # If compiled via PyInstaller or similar
            base_dir = os.path.dirname(sys.executable)
        else:
            # If running from source (core/sanitizer.py), we want to put it in the top level folder.
            core_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(core_dir)
            
        return os.path.join(base_dir, "sanitize_rules.json")

    def _get_default_rules(self) -> Dict[str, Any]:
        """Returns the default sanitization rules."""
        return {
            "remove_urls": True,
            "escape_ssml": True,
            "remove_emojis": True,
            "compress_spaces_and_newlines": True,
            "regex_delete": [
                r"[\*＊_＿\^＾\\￥#＃]",
                r"[~〜]",
                r"[\u200B-\u200D\uFEFF]",
                r"\(.*?\)",
                r"＼.*?／"
            ],
            "regex_replacements": [
                {"pattern": r"[/／|｜]", "replacement": "、"},
                {"pattern": r"※", "replacement": "注意、"},
                {"pattern": r"【|】|〔|〕|［|］|（|）|『|』", "replacement": "、"}
            ],
            "string_delete": [
                "@",
                "＠"
            ],
            "string_replacements": []
        }

    def load_rules(self) -> None:
        """Loads rules from the JSON file, or creates it if it doesn't exist."""
        if not os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "w", encoding="utf-8") as f:
                    json.dump(self.sanitize_rules, f, ensure_ascii=False, indent=4)
            except Exception as e:
                if self.logger:
                    self.logger.log("ルールの自動生成に失敗しました", str(e))
        else:
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    self.sanitize_rules = json.load(f)
            except Exception as e:
                self.sanitize_rules = self._get_default_rules()
                if self.logger:
                    self.logger.log(
                        "ルールの読み込みに失敗しました (JSON構文エラー等)", 
                        f"{e}\n※デフォルトのルールを適用して続行します。"
                    )

    def sanitize(self, text: str) -> str:
        """
        Applies all loaded rules to sanitize the input text.
        
        Args:
            text (str): The raw text to process.
            
        Returns:
            str: The sanitized text.
        """
        rules = self.sanitize_rules
        
        # 1. Remove URLs and Mermaid Blocks
        if rules.get("remove_urls", True):
            text = re.sub(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", "", text)
        text = re.sub(r'```mermaid.*?```', '', text, flags=re.DOTALL | re.IGNORECASE)
            
        # 2. Escape SSML special characters
        if rules.get("escape_ssml", True):
            text = text.replace("&", "アンド")
            text = text.replace("<", "")
            text = text.replace(">", "")
            text = text.replace('"', "")
            text = text.replace("'", "")
            
        # 3. Remove Emojis
        if rules.get("remove_emojis", True):
            # Removes surrogate pairs and standard emoji blocks roughly
            text = re.sub(r'[\U00010000-\U0010ffff]', '', text)

        # 4. Regex Replacements & Deletions
        # 4-A. Deletions (regex_delete)
        for pattern in rules.get("regex_delete", []):
            if pattern:
                try:
                    text = re.sub(pattern, "", text)
                except Exception as e:
                    if self.logger:
                        self.logger.log("サニタイズ正規表現エラー", f"削除パターン '{pattern}' でエラー: {e}")

        # 4-B. Replacements (regex_replacements)
        for rule in rules.get("regex_replacements", []):
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement", "")
            if pattern:
                try:
                    text = re.sub(pattern, replacement, text)
                except Exception as e:
                    if self.logger:
                        self.logger.log("サニタイズ正規表現エラー", f"パターン '{pattern}' でエラーが発生しました: {e}")
                
        # 5. String Replacements & Deletions
        # 5-A. Deletions (string_delete)
        for target in rules.get("string_delete", []):
            if target:
                text = text.replace(target, "")

        # 5-B. Replacements (string_replacements)
        for rule in rules.get("string_replacements", []):
            target = rule.get("target", "")
            replacement = rule.get("replacement", "")
            if target:
                text = text.replace(target, replacement)
                
        # 6. Compress Spaces and Newlines
        if rules.get("compress_spaces_and_newlines", True):
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r'[ 　]+', ' ', text)
            
        return text.strip()
