"""
URL configuration for djbackend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main.views import stream_view, main_view, archive_view, camera_source_view
from registration.views import login_view, registration_view
   
urlpatterns = [   
    path('', main_view, name='main-view'),
    path('stream/', stream_view, name='stream'),    
    path('archive/', archive_view, name='archive-view'),
    path('login/', login_view, name='login-view'),    
    path('registration/', registration_view, name='registration-view'),
    path('camera_source/', camera_source_view, name='camera-source'),
    path('admin/', admin.site.urls),
]