# Text-to-Speech (TTS) Application

[English](README.md) | [日本語](docs/README_ja.md) | [中文](docs/README_zh.md)

## Overview
This is a desktop application that converts text to speech using multiple TTS engines (like edge-tts, gTTS, and pyttsx3). It features a modern dark mode UI built with `ttkbootstrap` and processes text with customizable symbol sanitization rules.

**✨ New Features:** 
- **MP4 Video Export**: You can now export your TTS as an **MP4 video with real-time fluorescent yellow text highlighting** (karaoke style) on a clean light mode background when using the `edge-tts` engine. 
- **Auto-Pagination**: Long text is automatically split into multiple slides (every 10 lines) to prevent text overflow.
- **High-Speed & Markdown**: The output defaults to an interactive HTML player (2.5x speed). It fully supports rendering Markdown natively in your browser (e.g., `#` for headers, `**` for bold, `<aside>` for callouts, and `|` for tables). Markdown styling is preserved perfectly and highlights sync with the audio.
- **Silent Background Processing**: The app runs completely in the background without any annoying console windows popping up.

## Setup Instructions
This application uses a portable embedded Python environment, meaning you don't need to install Python on your system to run it.

1. **Initial Setup (Run Once)**
   Double-click `setup.bat` in this folder.
   This will automatically download a lightweight Python environment and install all necessary dependencies into a local `bin` folder. It will not modify your system paths or registry.

2. **Starting the App**
   Double-click `run.vbs`.
   The application will start immediately in the background. You can use this file to launch the app every time.

## Uninstallation
To completely remove the application, simply delete this entire folder. Since it uses a portable environment, no leftover files or registry keys will remain on your PC.

## Modifying the App
If you are a developer, the source code is located in the `core` folder (`core/main.pyw`). You can edit it directly, and the changes will take effect the next time you launch the app.
