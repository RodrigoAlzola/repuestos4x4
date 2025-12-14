from .base import *
import dj_database_url
import os

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
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,  # Agregar esto
    )
}

TRANSBANK_COMMERCE_CODE = os.environ.get('PROD_TRANSBANK_COMMERCE_CODE')
TRANSBANK_API_KEY = os.environ.get('PROD_TRANSBANK_API_KEY')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')  # noreply@4x4max.cl
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')  # Password de Zoho
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@4x4max.cl')
EMAIL_TIMEOUT = 10  # Timeout de 10 segundos

# Seguridad para producción
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')