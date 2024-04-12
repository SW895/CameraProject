from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.views import generic
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ArchiveVideo, CachedVideo
from .utils import gen
from datetime import timedelta, datetime
from .tasks import update_cache
import os
import socket
import json
import pytz
from django.utils.timezone import localtime


def main_view(request):
    return render(
        request,
        'main/main_page.html',
    )

#@login_required
def stream_view(request):
    # request camera list from DB
    camera_list = [1,2,3,4]

    return render(
        request,
        'main/stream_page.html',
        context={
            'camera_list':camera_list,
            'cam_list': json.dumps(camera_list),
        }        
    )

#@login_required
#def camera_source_view(request):
#    return StreamingHttpResponse(gen(),
#                                 content_type='multipart/x-mixed-replace; boundary=frame')

@login_required
def archive_view(request):
    videos = ArchiveVideo.objects.all()
    params = {}

    if request.GET:
        params = request.GET.dict()

        if 'date_created' in params.keys():
            date = datetime.strptime(params['date_created'], '%Y-%m-%d')
            videos = ArchiveVideo.objects.filter(date_created__date=date)
            del params['date_created']

        if params:
            videos = videos.filter(**params)

    return render(
        request,
        'main/archive_page.html',
        context={
            'params': params,
            'videos': videos,
            'full_url': str(request.get_full_path()),
        }
    )


class VideoDetailView(LoginRequiredMixin, generic.DetailView):
    model = ArchiveVideo
    template_name = 'main/archivevideo_detail.html'

    def get_context_data(self, *args, **kwargs):        
        timezone = pytz.timezone('Europe/Moscow')
        timeout = int(os.environ.get('CACHE_TIMEOUT', '60'))

        context = super(VideoDetailView, self).get_context_data(*args, **kwargs)
        video = ArchiveVideo.objects.get(pk=self.kwargs['pk'])
        video_name = localtime(video.date_created)
        video_name = video_name.strftime("%d_%m_%YT%H_%M_%S")
        if cache.get(video_name):
            context['video_name'] = video_name
            update_cache(video_name, timeout)
            return context
        else:
            sock = self.connect_to_server()
            if self.request_video(video_name, sock, timeout):
                context['video_name'] = video_name
                cache.add(video_name, True, timeout=timeout)
                record = CachedVideo(name=video_name,
                                     date_expire=datetime.now(tz=timezone) 
                                                + timedelta(seconds=timeout))
                record.save()
            else:
                context['video_name'] = None
            return context

    def request_video(self, video_name, sock, timeout=60):
        msg = {'request_type':'video_request', 'video_name':video_name}
        sock.send(json.dumps(msg).encode())
        reply = sock.recv(1024)
        sock.close()
       
        if reply.decode() == 'success':
            return True
        else:
            return False

    def connect_to_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'),
                          int(os.environ.get('INTERNAL_PORT', 20900))))
        except socket.error:
            sock.close()
            return None
        else:
            return sock
