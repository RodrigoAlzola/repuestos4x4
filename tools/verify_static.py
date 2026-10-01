"""Verifica collectstatic con manifiesto en una carpeta temporal local."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'ecom.settings.local'
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import override_settings

with override_settings(
    STATIC_ROOT=ROOT / 'var' / 'static-verification',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    },
):
    call_command('collectstatic', interactive=False, verbosity=0)
    for name in ['css/catalog.css', 'css/typography.css', 'js/catalog.js', 'js/garage.js',
                 'fonts/montserrat/Montserrat-variable.ttf', 'images/logo-brand.png',
                 'images/part-placeholder.svg', 'images/marketing/IMG-home.png',
                 'images/marketing/emblema_positivo.jpg']:
        stored = staticfiles_storage.stored_name(name)
        assert staticfiles_storage.exists(stored), name
        print(f'OK {name} -> {stored}')
