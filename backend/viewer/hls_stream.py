import os
import uuid
import json
import subprocess
import time # Import time for the waiting logic
from urllib.parse import urlparse, urlunparse
from django.http import JsonResponse, Http404, FileResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from django.utils.encoding import smart_str
from django.shortcuts import redirect

HLS_ROOT = settings.HLS_MEDIA_ROOT
FFMPEG_LOG_DIR = settings.FFMPEG_LOG_DIR
os.makedirs(HLS_ROOT, exist_ok=True)
os.makedirs(FFMPEG_LOG_DIR, exist_ok=True)

# Dictionary to keep track of active FFmpeg processes by stream_id
# In a production system, this would need a more robust persistence mechanism
# like a database or cache. For this example, a dictionary is sufficient.
active_ffmpeg_processes = {}

@csrf_exempt
def start_hls_stream(request):
    """
    POST: {"url": ..., "username": ..., "password": ...}
    Returns: {"stream_id": ..., "playlist_url": ...}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}
    rtsp_url_from_user = data.get('url')
    username_override = data.get('username')
    password_override = data.get('password')

    if not rtsp_url_from_user:
        return JsonResponse({'error': 'Missing RTSP URL'}, status=400)

    try:
        parsed_url = urlparse(rtsp_url_from_user)
        
        final_hostname = parsed_url.hostname
        if not final_hostname:
            return JsonResponse({'error': 'Invalid RTSP URL: Hostname missing.'}, status=400)

        # Determine the effective username and password.
        # Prioritize overrides. If override is an empty string, treat as not provided (fall back to parsed_url).
        effective_username = username_override if username_override else parsed_url.username
        effective_password = password_override if password_override else parsed_url.password
        
        # If password came from parsed_url (i.e., no override) and contains '@',
        # it's likely from a 'user:pass@@host' malformed URL.
        # The actual password is the part before the first '@' in such cases.
        if not password_override and parsed_url.password and '@' in parsed_url.password:
            effective_password = parsed_url.password.split('@', 1)[0]

        # Reconstruct netloc using the (potentially cleaned) credentials and original hostname/port
        netloc_parts = []
        if effective_username:
            userinfo = effective_username
            if effective_password: # Only add colon if password actually exists
                userinfo += f":{effective_password}"
            netloc_parts.append(f"{userinfo}@")
        
        # final_hostname is parsed_url.hostname, extracted earlier
        netloc_parts.append(final_hostname) 
        if parsed_url.port:
            netloc_parts.append(f":{parsed_url.port}")
        
        new_netloc_str = "".join(netloc_parts)
        
        final_rtsp_url_for_ffmpeg = urlunparse((
            parsed_url.scheme if parsed_url.scheme else 'rtsp',
            new_netloc_str,
            parsed_url.path if parsed_url.path else '/',
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))
    except Exception as e:
        # Added specific logging for URL parsing errors
        print(f"Error parsing RTSP URL: {e}")
        return JsonResponse({'error': f'Error parsing RTSP URL: {str(e)}'}, status=400)

    stream_id = str(uuid.uuid4())
    stream_dir = os.path.join(HLS_ROOT, stream_id)
    os.makedirs(stream_dir, exist_ok=True)
    
    playlist_path = os.path.join(stream_dir, 'stream.m3u8')
    
    ffmpeg_log_filename = f"ffmpeg_{stream_id}.log"
    log_path = os.path.join(FFMPEG_LOG_DIR, ffmpeg_log_filename)

    ffmpeg_cmd = [
        'ffmpeg',
        '-fflags', 'nobuffer',
        '-rtsp_transport', 'tcp',
        '-rtsp_flags', 'prefer_tcp',
        '-i', final_rtsp_url_for_ffmpeg,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',  # Faster encoding
        '-tune', 'zerolatency',  # Minimize latency
        '-profile:v', 'baseline',  # Simpler profile for better compatibility
        '-b:v', '2000k',  # Target bitrate
        '-maxrate', '2500k',  # Maximum bitrate
        '-bufsize', '5000k',  # Buffer size
        '-g', '30',  # Keyframe interval
        # '-an',  # No audio - REMOVED to process audio
        '-c:a', 'aac',      # Encode audio to AAC
        '-b:a', '128k',     # Audio bitrate 128k
        '-f', 'hls',
        '-hls_time', '2',
        '-hls_list_size', '10',
        '-hls_flags', 'delete_segments+append_list+independent_segments',
        '-hls_segment_type', 'mpegts',
        '-hls_segment_filename', os.path.join(stream_dir, 'stream%d.ts'),
        playlist_path
    ]
    
    try:
        log_file = open(log_path, "a")
        process = subprocess.Popen(ffmpeg_cmd, stdout=log_file, stderr=log_file)
        # Store the process to potentially manage it later (e.g., stopping old streams)
        active_ffmpeg_processes[stream_id] = process
        return JsonResponse({'stream_id': stream_id, 'playlist_url': f'/hls/{stream_id}/stream.m3u8', 'log_file': log_path})
    except Exception as e:
        return JsonResponse({'error': f"Failed to start FFmpeg: {str(e)}"}, status=500)

def hls_serve(request, stream_id, filename):
    # Serve .m3u8 and .ts files with correct MIME types
    stream_dir = os.path.join(HLS_ROOT, stream_id)
    file_path = os.path.join(stream_dir, filename)
    
    # --- Add waiting logic here ---
    max_wait_time = 10 # seconds
    wait_interval = 0.5 # seconds
    waited_time = 0
    
    while not os.path.exists(file_path) and waited_time < max_wait_time:
        time.sleep(wait_interval)
        waited_time += wait_interval
    # --- End waiting logic ---

    if not os.path.exists(file_path):
        # If file still doesn't exist after waiting, raise 404
        raise Http404("File does not exist")

    if filename.endswith('.m3u8'):
        content_type = 'application/vnd.apple.mpegurl'
    elif filename.endswith('.ts'):
        content_type = 'video/mp2t'
    else:
        content_type = 'application/octet-stream'

    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Access-Control-Allow-Origin'] = '*'  # Allow CORS for HLS segments
    return response
