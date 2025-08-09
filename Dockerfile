FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY ./shopsite .


EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "shopsite.wsgi:application"]
