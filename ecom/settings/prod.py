from .base import *

DEBUG = True

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = [
    'repuesto4x4.com',
    'www.repuesto4x4.com',  # Agregar
    '4x4max.cl',  # Sin https://
    'www.4x4max.cl',
    'repuestos4x4-production.up.railway.app',
]

CSRF_TRUSTED_ORIGINS = [
    'https://repuesto4x4.com',
    'https://www.repuesto4x4.com',  # Agregar
    'https://4x4max.cl',  # Agregar
    'https://www.4x4max.cl',  # Agregar
    'https://repuestos4x4-production.up.railway.app',
]

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

TRANSBANK_COMMERCE_CODE = os.environ.get('PROD_TRANSBANK_COMMERCE_CODE')
TRANSBANK_API_KEY = os.environ.get('PROD_TRANSBANK_API_KEY')


# Seguridad para producción
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')