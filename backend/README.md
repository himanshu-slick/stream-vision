# RTSP Stream Viewer Backend

This is the Django backend for the RTSP Stream Viewer project. It uses Django Channels for WebSocket support and FFmpeg for processing RTSP streams.

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Start the development server (ASGI):
   ```bash
   daphne -b 0.0.0.0 -p 8000 backend.asgi:application
   ```

## Features
- Accepts RTSP stream URLs via WebSocket
- Uses FFmpeg to process and relay streams
- Handles multiple streams and errors gracefully

## Note
- Make sure FFmpeg is installed on your system and available in PATH.
