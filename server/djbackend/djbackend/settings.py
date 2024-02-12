from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', '111')
DEBUG = bool(os.environ.get('DEBUG', 0))
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1').split(' ')
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:1337').split(' ')
AUTH_USER_MODEL = 'registration.CustomUser'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'main.apps.MainConfig',
    'registration.apps.RegistrationConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'djbackend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR/ 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'djbackend.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = '/'

# DB
DATABASES = {
    'default': 
        {
        'ENGINE': os.environ.get('POSTGRES_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('POSTGRES_DB', 'dj_test'),
        'USER': os.environ.get('POSTGRES_USER', 'test_dj'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', '123'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }    
    }

# Redis 
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": 'redis://{}:{}@{}:{}'.format(os.environ.get('REDIS_USER', 'default'),
                                                 os.environ.get('REDIS_PASSWORD', '123'),
                                                 os.environ.get('REDIS_HOST', '127.0.0.1'),
                                                 os.environ.get('REDIS_PORT', '6379'))
        }
    }

# Celery
CELERY_BROKER_URL = 'redis://{}:{}/0'.format(os.environ.get('REDIS_HOST', '127.0.0.1'),
                                             os.environ.get('REDIS_PORT', '6379'))
CELERY_RESULT_BACKEND = 'redis://{}:{}/0'.format(os.environ.get('REDIS_HOST', '127.0.0.1'),
                                                 os.environ.get('REDIS_PORT', '6379'))

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = bool(os.environ.get('EMAIL_USE_TLS', 1))
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_FROM')