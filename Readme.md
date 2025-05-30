# StreamVision - RTSP to HLS Streaming Application

## 1. Overview

StreamVision is a web application designed to stream video content from RTSP (Real Time Streaming Protocol) sources. It features a Next.js frontend for user interaction and a Django backend that uses FFmpeg to convert RTSP streams into HLS (HTTP Live Streaming) format. This allows for easy viewing of RTSP streams directly in modern web browsers on various devices.

## 2. Key Features

- **Dynamic RTSP to HLS Conversion:** Converts live RTSP streams to HLS on-the-fly.
- **Multiple Stream Support:** Allows users to add and view multiple RTSP streams simultaneously.
- **Web-Based Viewing:** Streams are viewable directly in the browser using Hls.js, with a fallback to native HLS support.
- **User-Friendly Interface:** Simple interface to add, manage, and view streams.
- **Expandable Video Player:** Players can be expanded for a focused view.
- **Responsive Design:** Adapts to different screen sizes, including mobile devices.
- **Dark Mode:** Includes a theme toggle for user preference.

## 3. Technology Stack

- **Frontend:**
  - Next.js (React Framework)
  - TypeScript
  - Hls.js (JavaScript HLS client)
  - Tailwind CSS (Styling)
  - Shadcn/ui (UI Components)
  - Lucide React (Icons)
- **Backend:**
  - Django (Python Web Framework)
  - Django REST framework (Potentially, for API endpoints)
  - FFmpeg (For video processing and HLS conversion)
- **Database:**
  - SQLite (Default for Django, can be configured for others)
- **Version Control:**
  - Git

## 4. Project Structure

Stream Vision/
backend/
backend/ # Django project settings (settings.py, urls.py, etc.)
viewer/
migrations/
hls_stream.py # Core HLS streaming logic, FFmpeg commands
models.py
admin.py
apps.py
tests.py
urls.py # App-specific URLs
views.py # (May contain simple views or be integrated into hls_stream.py)
ffmpeg_logs/ # Logs generated by FFmpeg processes
hls_media/ # Temporary storage for HLS segments (.m3u8, .ts files)
manage.py # Django management script
frontend/
app/ # Next.js App Router
viewer/
page.tsx # Main page for viewing streams
layout.tsx
page.tsx # Home page
components/ # Reusable UI components (e.g., Shadcn/ui)
ui/
hooks/
use-mobile.ts
lib/
api.ts # Frontend API calls to the backend
public/ # Static assets
.gitignore
next.config.mjs
package.json
postcss.config.mjs
tailwind.config.ts
tsconfig.json
README.md # This file

## 5. Prerequisites

- Node.js (v18.x or later recommended)
- npm or yarn (or pnpm, as indicated by `.pnpm-debug.log` in `.gitignore`)
- Python (v3.8 or later recommended)
- pip (Python package installer)
- FFmpeg: Ensure FFmpeg is installed and accessible in your system's PATH.
- An RTSP stream source (e.g., an IP camera).

## 6. Setup and Installation

### 6.1. Backend (Django)

1.  **Navigate to the backend directory:**

    ```bash
    cd backend
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Python dependencies:**
    (Assuming a `requirements.txt` file exists or will be created. If not, list key dependencies like Django)

    ```bash
    pip install Django djangorestframework # Add other dependencies if any
    # If you have a requirements.txt:
    # pip install -r requirements.txt
    ```

4.  **Apply database migrations:**

    ```bash
    python manage.py migrate
    ```

5.  **Create necessary directories if they don't exist:**
    Make sure `ffmpeg_logs` and `hls_media` directories exist inside the `backend` directory.
    ```bash
    mkdir -p ffmpeg_logs
    mkdir -p hls_media
    ```

### 6.2. Frontend (Next.js)

1.  **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**
    Using npm:
    ```bash
    npm install
    ```
    Or using yarn:
    ```bash
    yarn install
    ```
    Or using pnpm:
    ```bash
    pnpm install
    ```

## 7. How to Run the Application

### 7.1. Start the Backend Server

1.  Navigate to the `backend` directory.
2.  Activate your virtual environment if you created one.
3.  Run the Django development server (default port is 8000):
    ```bash
    python manage.py runserver
    ```
    You can specify a different port if needed: `python manage.py runserver 0.0.0.0:8001`

### 7.2. Start the Frontend Development Server

1.  Navigate to the `frontend` directory.
2.  Run the Next.js development server (default port is 3000):
    Using npm:

    ```bash
    npm run dev
    ```

    Or using yarn:

    ```bash
    yarn dev
    ```

    Or using pnpm:

    ```bash
    pnpm dev
    ```

3.  Open your browser and navigate to `http://localhost:3000` (or the port your frontend is running on).

## 8. Streaming Workflow

1.  **User Action:** The user enters an RTSP URL, username, and password into the frontend interface and clicks "Add Stream".
2.  **Frontend Request:** The Next.js frontend sends a request to the Django backend API (e.g., `/api/start_stream/`) with the RTSP details.
3.  **Backend Processing (Django & FFmpeg):**
    - The Django backend receives the request.
    - It generates a unique stream ID.
    - It constructs an FFmpeg command to:
      - Connect to the provided RTSP URL.
      - Transcode the video (and audio) into HLS format.
      - Output `.m3u8` playlist files and `.ts` segment files into a subdirectory within `backend/hls_media/<stream_id>/`.
    - FFmpeg process is started as a background subprocess.
    - The backend responds to the frontend with the `stream_id` and the base URL for the HLS playlist.
4.  **Frontend Playback (Hls.js):**
    - The frontend receives the `stream_id`.
    - It constructs the HLS playlist URL (e.g., `http://localhost:8000/hls/<stream_id>/stream.m3u8`).
    - Hls.js (or the native video player) is initialized with this URL.
    - The player requests the `.m3u8` playlist from the Django backend.
5.  **Backend HLS Serving:**
    - The Django backend has an endpoint (e.g., `/hls/<stream_id>/<filename>`) that serves the `.m3u8` and `.ts` files from the `backend/hls_media/<stream_id>/` directory.
    - The player then requests the individual `.ts` segments as specified in the playlist, and playback begins.

## 9. Key Files and Directories

- **`backend/viewer/hls_stream.py`**: Contains the core logic for starting FFmpeg processes and serving HLS files.
- **`backend/viewer/urls.py`**: Defines URL patterns for the backend API endpoints related to streaming.
- **`backend/hls_media/`**: Storage for generated HLS playlist and segment files. Each stream gets its own subdirectory.
- **`backend/ffmpeg_logs/`**: Stores log files for each FFmpeg process, useful for debugging.
- **`frontend/app/viewer/page.tsx`**: The main React component for the stream viewing interface, handling user input, API calls, and video player initialization.
- **`frontend/lib/api.ts`**: Contains functions for making API calls from the frontend to the backend.

## 10. Troubleshooting

- **404 Error for `stream.m3u8`:**
  - Check the Django server console for errors when adding the stream.
  - Examine the corresponding FFmpeg log file in `backend/ffmpeg_logs/ffmpeg_<stream_id>.log`. This often reveals issues like incorrect RTSP URLs, authentication failures, or FFmpeg command errors.
  - Ensure the `backend/hls_media/<stream_id>/` directory is being created and populated with files. If it's empty, FFmpeg failed to produce output.
  - Verify the RTSP URL is correct and accessible (e.g., test with VLC media player).
  - Check for "406 Not Acceptable" errors in FFmpeg logs, which might indicate issues with audio/video track negotiation (e.g., FFmpeg trying to ignore an audio track the camera insists on sending).
- **FFmpeg Not Found:** Ensure FFmpeg is installed correctly and its executable is in your system's PATH.
- **CORS Issues:** The Django backend includes CORS headers, but ensure your frontend requests are correctly reaching the backend.
- **Video Player Issues:**
  - Check the browser's developer console for errors from Hls.js or the native video element.
  - Ensure Hls.js is correctly initialized and attached to the video element.
