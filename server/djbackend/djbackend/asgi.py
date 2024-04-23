"""
ASGI config for djbackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_project.settings")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djbackend.settings')
import django
django.setup()
#application = get_default_application()
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
from main.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        'http':get_asgi_application(),
        'websocket': AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)