FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Upgrde pip and install dependencies
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONPATH=/app
CMD ["gunicorn", "-b", "0.0.0.0:8000", "shopsite.wsgi:application"]
