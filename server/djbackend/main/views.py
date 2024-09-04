import os
import socket
import json
import pytz
import logging
from django.utils.timezone import localtime
from datetime import timedelta, datetime
from django.shortcuts import render
from django.views import generic
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from .models import ArchiveVideo, CachedVideo, Camera
from .tasks import update_cache


def main_view(request):
    return render(
        request,
        'main/main_page.html',
    )


@login_required
def stream_view(request):
    camera_list = Camera.objects.filter(is_active=True)
    simplified_camera_list = []
    for camera in camera_list:
        simplified_camera_list.append(camera.camera_name)
    return render(
        request,
        'main/stream_page.html',
        context={
            'camera_list': camera_list,
            'cam_list': json.dumps(simplified_camera_list),
        }
    )


@login_required
def archive_view(request):
    cameras = Camera.objects.all()
    videos = ArchiveVideo.objects.all()
    params = {}
    det_fields = []
    page_number = 1
    for field in ArchiveVideo._meta.get_fields():
        if field.name.find('_det') > 0:
            det_fields.append((field.name,
                               field.name.removesuffix('_det').title()))

    if request.GET:
        params = request.GET.dict()
        if 'date_created' in params.keys():
            date = datetime.strptime(params['date_created'], '%Y-%m-%d')
            videos = ArchiveVideo.objects.filter(date_created__date=date)
            del params['date_created']
        if 'page' in params.keys():
            page_number = request.GET.get("page")
            del params['page']
        if params:
            videos = videos.filter(**params)

    paginator = Paginator(videos, 10)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        'main/archive_page.html',
        context={
            'params': params,
            'cameras': cameras,
            'det_fields': det_fields,
            'full_url': str(request.get_full_path()),
            'page_obj': page_obj,
            'current_page': page_number,
        }
    )

import logging
class VideoDetailView(LoginRequiredMixin, generic.DetailView):
    model = ArchiveVideo
    template_name = 'main/archivevideo_detail.html'

    def get_context_data(self, **kwargs):
        timezone = pytz.timezone('Europe/Moscow')
        timeout = int(os.environ.get('CACHE_TIMEOUT', '60'))
        context = super(VideoDetailView, self).get_context_data(**kwargs)
        video = ArchiveVideo.objects.get(pk=self.kwargs['pk'])
        video_name = localtime(video.date_created)\
            .strftime("%d_%m_%YT%H_%M_%S")
        request = {'request_type': 'video_request',
                   'video_name': (video_name + '|' + video.camera.camera_name)}
        if cache.get(video_name):
            context['video_name'] = video_name
            update_cache(video_name, timeout)
            return context
        else:
            if self.request_video(request, timeout):
                context['video_name'] = video_name
                cache.add(video_name, True, timeout=timeout)
                record = CachedVideo(
                    name=video_name,
                    date_expire=datetime.now(tz=timezone)
                    + timedelta(seconds=timeout))
                record.save()
                context['video_name'] = video_name
            else:
                context['video_name'] = None
            return context

    def request_video(self, request, timeout=60):
        sock = self.connect_to_server()
        sock.send(json.dumps(request).encode())
        reply = sock.recv(1024)
        logging.critical(reply.decode())
        if reply.decode() == 'accepted':
            reply = sock.recv(1024)
            if reply.decode() == 'success':
                sock.close()
                return True
        else:
            sock.close()
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
