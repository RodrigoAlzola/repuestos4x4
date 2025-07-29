from .base import *

DEBUG = True

# SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = ['https://repuesto4x4.com', 'repuesto4x4.com', 'repuestos4x4-production.up.railway.app', 'https://repuestos4x4-production.up.railway.app']
CSRF_TRUSTED_ORIGINS = ['https://repuesto4x4.com', 'https://repuestos4x4-production.up.railway.app']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'railway',
        'USER': 'postgres',
        'PASSWORD': os.environ['DB_PASSWORD_YO'],
        'HOST': 'ballast.proxy.rlwy.net',
        'PORT': '45961',
    }
}