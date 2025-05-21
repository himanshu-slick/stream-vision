import os
import uuid
import json
import subprocess
import time
from urllib.parse import urlparse, urlunparse
from django.http import JsonResponse, Http404, FileResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import tempfile
import boto3
from botocore.exceptions import ClientError

# Dictionary to keep track of active FFmpeg processes by stream_id
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

        # Determine the effective username and password
        effective_username = username_override if username_override else parsed_url.username
        effective_password = password_override if password_override else parsed_url.password
        
        if not password_override and parsed_url.password and '@' in parsed_url.password:
            effective_password = parsed_url.password.split('@', 1)[0]

        netloc_parts = []
        if effective_username:
            userinfo = effective_username
            if effective_password:
                userinfo += f":{effective_password}"
            netloc_parts.append(f"{userinfo}@")
        
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
        print(f"Error parsing RTSP URL: {e}")
        return JsonResponse({'error': f'Error parsing RTSP URL: {str(e)}'}, status=400)

    stream_id = str(uuid.uuid4())
    stream_dir = f"{settings.HLS_MEDIA_ROOT}/{stream_id}"
    
    # Create a temporary directory for FFmpeg to write to
    with tempfile.TemporaryDirectory() as temp_dir:
        playlist_path = os.path.join(temp_dir, 'stream.m3u8')
        
        ffmpeg_log_filename = f"ffmpeg_{stream_id}.log"
        log_path = os.path.join(temp_dir, ffmpeg_log_filename)

        ffmpeg_cmd = [
            'ffmpeg',
            '-fflags', 'nobuffer',
            '-rtsp_transport', 'tcp',
            '-rtsp_flags', 'prefer_tcp',
            '-i', final_rtsp_url_for_ffmpeg,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-profile:v', 'baseline',
            '-b:v', '2000k',
            '-maxrate', '2500k',
            '-bufsize', '5000k',
            '-g', '30',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-f', 'hls',
            '-hls_time', '2',
            '-hls_list_size', '10',
            '-hls_flags', 'delete_segments+append_list+independent_segments',
            '-hls_segment_type', 'mpegts',
            '-hls_segment_filename', os.path.join(temp_dir, 'stream%d.ts'),
            playlist_path
        ]
        
        try:
            log_file = open(log_path, "a")
            process = subprocess.Popen(ffmpeg_cmd, stdout=log_file, stderr=log_file)
            active_ffmpeg_processes[stream_id] = process

            # Wait for the first playlist file to be generated
            max_wait_time = 10  # Maximum time to wait in seconds
            start_time = time.time()
            while not os.path.exists(playlist_path):
                if time.time() - start_time > max_wait_time:
                    process.terminate()
                    return JsonResponse({'error': 'Timeout waiting for stream to start'}, status=500)
                time.sleep(0.5)

            # Upload the initial playlist file
            with open(playlist_path, 'rb') as f:
                default_storage.save(f'{stream_dir}/stream.m3u8', ContentFile(f.read()))

            # Start a background task to monitor and upload files
            def monitor_and_upload():
                while True:
                    if not os.path.exists(playlist_path):
                        time.sleep(0.5)
                        continue
                    
                    # Upload playlist file
                    with open(playlist_path, 'rb') as f:
                        default_storage.save(f'{stream_dir}/stream.m3u8', ContentFile(f.read()))
                    
                    # Upload any new .ts files
                    for filename in os.listdir(temp_dir):
                        if filename.endswith('.ts'):
                            file_path = os.path.join(temp_dir, filename)
                            with open(file_path, 'rb') as f:
                                default_storage.save(f'{stream_dir}/{filename}', ContentFile(f.read()))
                    
                    time.sleep(1)  # Check every second

            import threading
            monitor_thread = threading.Thread(target=monitor_and_upload, daemon=True)
            monitor_thread.start()

            return JsonResponse({
                'stream_id': stream_id,
                'playlist_url': f'{settings.MEDIA_URL}{stream_dir}/stream.m3u8',
                'log_file': f'{settings.MEDIA_URL}{settings.FFMPEG_LOG_DIR}/{ffmpeg_log_filename}'
            })
        except Exception as e:
            return JsonResponse({'error': f"Failed to start FFmpeg: {str(e)}"}, status=500)

def hls_serve(request, stream_id, filename):
    try:
        file_path = f"{settings.HLS_MEDIA_ROOT}/{stream_id}/{filename}"
        if not default_storage.exists(file_path):
            raise Http404("File does not exist")

        if filename.endswith('.m3u8'):
            content_type = 'application/vnd.apple.mpegurl'
        elif filename.endswith('.ts'):
            content_type = 'video/mp2t'
        else:
            content_type = 'application/octet-stream'

        file = default_storage.open(file_path)
        response = FileResponse(file, content_type=content_type)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")

@csrf_exempt
def stop_hls_stream(request, stream_id):
    """
    Stop an HLS stream and clean up its files
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        # Stop the FFmpeg process if it's running
        if stream_id in active_ffmpeg_processes:
            process = active_ffmpeg_processes[stream_id]
            if process.poll() is None:  # If process is still running
                process.terminate()
                process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
            del active_ffmpeg_processes[stream_id]

        # Clean up S3 files
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        # List all objects in the stream directory
        stream_prefix = f"{settings.HLS_MEDIA_ROOT}/{stream_id}/"
        try:
            response = s3_client.list_objects_v2(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Prefix=stream_prefix
            )
            
            # Delete all objects in the stream directory
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                if objects_to_delete:
                    s3_client.delete_objects(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Delete={'Objects': objects_to_delete}
                    )
        except ClientError as e:
            print(f"Error cleaning up S3 files: {e}")
            return JsonResponse({'error': 'Failed to clean up stream files'}, status=500)

        return JsonResponse({'message': 'Stream stopped and cleaned up successfully'})
    except Exception as e:
        return JsonResponse({'error': f'Error stopping stream: {str(e)}'}, status=500)
