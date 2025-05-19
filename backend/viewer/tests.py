from django.test import TestCase, Client
from django.urls import reverse
import os
from django.conf import settings

class HlsStreamTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rtsp_url = "rtsp://example.com/stream"  # Use a dummy or mock URL

    def test_start_hls_missing_url(self):
        response = self.client.post(reverse('start_hls_stream'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_start_hls_success(self):
        response = self.client.post(
            reverse('start_hls_stream'),
            data={'url': self.rtsp_url},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('playlist_url', response.json())
        self.assertIn('stream_id', response.json())

    def test_hls_serve_404(self):
        response = self.client.get('/hls/nonexistent/stream.m3u8')
        self.assertEqual(response.status_code, 404)

    def test_hls_folder_created(self):
        response = self.client.post(
            reverse('start_hls_stream'),
            data={'url': self.rtsp_url},
            content_type='application/json'
        )
        data = response.json()
        stream_id = data.get('stream_id')
        hls_dir = os.path.join(settings.HLS_MEDIA_ROOT, stream_id)
        self.assertTrue(os.path.exists(hls_dir)) 