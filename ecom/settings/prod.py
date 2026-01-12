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

EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'no-reply@4x4max.cl'
SENDGRID_SANDBOX_MODE_IN_DEBUG = False
SENDGRID_SANDBOX_MODE = False  # Por si acaso

# Seguridad para producción
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# ==================== EMAIL DEBUG ====================
import logging

# Configurar logging de email
# logging.basicConfig(level=logging.DEBUG)
# email_logger = logging.getLogger('django.core.mail')
# email_logger.setLevel(logging.DEBUG)

# Print config al iniciar
# print("\n" + "="*60)
# print("EMAIL CONFIGURATION:")
# print(f"Backend: {EMAIL_BACKEND}")