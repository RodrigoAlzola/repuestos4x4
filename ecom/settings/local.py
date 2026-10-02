"""Entorno local: copia independiente del catálogo y correo en consola."""
from .base import *

DEBUG = True
SECRET_KEY = '4x4max-local-development-only-not-for-production'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR.parent / 'var' / 'db.sqlite3'}}
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
BREVO_API_KEY = ''
TRANSBANK_COMMERCE_CODE = ''
TRANSBANK_API_KEY = ''
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
MIDDLEWARE = [m for m in MIDDLEWARE if 'whitenoise' not in m]
INSTALLED_APPS = [a for a in INSTALLED_APPS if 'whitenoise' not in a]

# Leer plantillas en cada petición para iterar HTML con sólo recargar el navegador.
TEMPLATES = [dict(config, APP_DIRS=False, OPTIONS={
    **config['OPTIONS'], 'loaders': [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ],
}) for config in TEMPLATES]
