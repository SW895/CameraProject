from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.views import generic
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ArchiveVideo, CachedVideo
from .utils import gen
from datetime import timedelta, datetime
import os
import socket


def main_view(request):
    return render(
        request,
        'main/main_page.html',
    )


@login_required
def stream_view(request):
    return render(
        request,
        'main/stream_page.html',
    )


@login_required
def camera_source_view(request):
    return StreamingHttpResponse(gen(),
                                 content_type='multipart/x-mixed-replace; boundary=frame')


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

        timeout = int(os.environ.get('CACHE_TIMEOUT', '60'))
        context = super(VideoDetailView, self).get_context_data(*args, **kwargs)
        video = ArchiveVideo.objects.get(pk=self.kwargs['pk'])
        video_name = video.date_created.strftime("%d_%m_%YT%H_%M_%S")

        if cache.get(video_name):
            context['video_name'] = video_name
            cache.set(video_name, True, timeout=timeout)
            record = CachedVideo.objects.get(name=video_name)
            record.date_expire = datetime.now() + timedelta(seconds=timeout)
            record.save()
            return context

        else:
            msg = 'Video' + ' ' + video_name
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            try:
                sock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'),
                              int(os.environ.get('INTERNAL_PORT', 20900))))
            except socket.error:
                context['video_name'] = None
                sock.close()
                return context

            sock.send(msg.encode())
            reply = sock.recv(1024)

            if reply.decode() == 'Success':
                context['video_name'] = video_name
                cache.set(video_name, True, timeout=timeout)
                record = CachedVideo(name=video_name,
                                     date_expire=datetime.now() + timedelta(seconds=timeout))
                record.save()
            else:
                context['video_name'] = None

            sock.close()
            return context
