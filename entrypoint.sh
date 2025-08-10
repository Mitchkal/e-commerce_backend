#!/bin/bash
set -e

echo "waiting for database..."
python manage.py wait_for_db

if [[ "$1" == "celery" ]]; then
    echo "waiting for redis"
    python manage.py wait_for_redis
fi

# Run migrations from web service
if [[ "$1" == "gunicorn" ]]; then

    # Apply database migrations
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Seeding the database..."
    python manage.py seed_products --csv-path Divi-Engine-WooCommerce-Sample-Products.csv --download-images
fi
# Start celery worker
# echo "starting Celery worker..."
# celery -A shopsite worker --loglevel=info

# Keep the container running by executing main command
echo "starting service: $@"
exec "$@"

