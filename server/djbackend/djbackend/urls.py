from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main import views as main
from registration import views as reg

urlpatterns = [
    path('',
         main.main_view,
         name='main'),
    path('stream/',
         main.stream_view,
         name='stream'),
    path('archive/',
         main.archive_view,
         name='archive'),
    path('archive/<int:pk>',
         main.VideoDetailView.as_view(),
         name='video-detail'),
    path('registration/',
         reg.registration_view,
         name='registration'),
    path('registration_confirm/',
         reg.registration_confirm_view,
         name='registration-confirm'),
    path('accounts/',
         include('django.contrib.auth.urls')),
    path('admin/',
         admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
