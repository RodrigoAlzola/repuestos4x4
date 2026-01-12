web: python manage.py migrate && gunicorn ecom.wsgi:application --log-file -
worker: while true; do python manage.py process_email_updates --mark-as-read; sleep 86400; done