gunicorn --reload   --bind 0.0.0.0:8000 shopsite.wsgi:application   --access-logfile /var/log/gunicorn/access.log   --error-logfile /var/log/gunicorn/error.log   --log-level debug
