import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

class StreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'message': 'WebSocket connection established.'
        }))

    async def disconnect(self, close_code):
        # On disconnect, FFmpeg process will be killed automatically by the event loop
        pass

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        url = data.get('url')
        username = data.get('username')
        password = data.get('password')

        # Build FFmpeg command for MJPEG output
        # If credentials provided, insert them into the URL
        if username and password:
            url_parts = url.split('rtsp://')
            if len(url_parts) == 2:
                url = f"rtsp://{username}:{password}@{url_parts[1]}"
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', url,
            '-f', 'mjpeg',
            '-q:v', '5',
            '-update', '1',
            '-r', '2',  # 2 fps for demo
            '-'
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': f'Could not start FFmpeg: {str(e)}'
            }))
            return

        await self.send(text_data=json.dumps({'message': 'Streaming started'}))

        # Stream the RTSP as a continuous live stream
        boundary = b'\xff\xd8'  # JPEG SOI marker
        buffer = b''
        ffmpeg_stderr = b''
        frame_count = 0
        try:
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    # Try to read from stderr for errors
                    ffmpeg_stderr += await process.stderr.read(4096)
                    break
                buffer += chunk
                # Look for JPEG SOI/EOI markers
                while True:
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9', start)
                    if start != -1 and end != -1:
                        jpeg = buffer[start:end+2]
                        buffer = buffer[end+2:]
                        await self.send(bytes_data=jpeg)
                        frame_count += 1
                    else:
                        break
            # After streaming, check for FFmpeg errors
            if frame_count == 0:
                # Read remaining stderr
                while True:
                    err_chunk = await process.stderr.read(4096)
                    if not err_chunk:
                        break
                    ffmpeg_stderr += err_chunk
                err_text = ffmpeg_stderr.decode(errors='ignore').splitlines()
                last_lines = '\n'.join(err_text[-10:])  # Send last 10 lines of error
                await self.send(text_data=json.dumps({'error': f'No frames received. FFmpeg error:\n{last_lines}'}))
            await self.send(text_data=json.dumps({'message': f'Stream ended after {frame_count} frames'}))
        except Exception as e:
            # Read remaining stderr
            while True:
                err_chunk = await process.stderr.read(4096)
                if not err_chunk:
                    break
                ffmpeg_stderr += err_chunk
            err_text = ffmpeg_stderr.decode(errors='ignore').splitlines()
            last_lines = '\n'.join(err_text[-10:])
            await self.send(text_data=json.dumps({'error': f'Error streaming: {str(e)}\nFFmpeg error:\n{last_lines}'}))
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
