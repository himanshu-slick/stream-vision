from django.urls import path, re_path
from . import hls_stream

urlpatterns = [
    path('start_hls/', hls_stream.start_hls_stream, name='start_hls_stream'),
    re_path(r'^hls/(?P<stream_id>[\w-]+)/(?P<filename>.+)$', hls_stream.hls_serve, name='hls_serve'),
]
