from .base import *

DEBUG = True

SECRET_KEY = os.environ.get('SECRET_KEY')

ALLOWED_HOSTS = ['localhost', '127.0.0.1']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

TRANSBANK_COMMERCE_CODE = os.environ.get('DEV_TRANSBANK_COMMERCE_CODE')
TRANSBANK_API_KEY = os.environ.get('DEV_TRANSBANK_API_KEY')