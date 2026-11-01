web: python manage.py migrate --noinput && python manage.py collectstatic --clear --noinput && gunicorn portfolio.wsgi:application --bind 0.0.0.0:$PORT
