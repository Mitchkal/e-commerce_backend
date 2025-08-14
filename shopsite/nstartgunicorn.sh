gunicorn --reload   --bind 0.0.0.0:8000 shopsite.wsgi:application   --access-logfile '-'   --error-logfile '-'   --log-level debug   > >(tee -a access.log)   2> >(tee -a error.log >&2)
