FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV PORT 8080
# Use gunicorn for production. Expose port 8080 for Cloud Run.
CMD exec gunicorn --bind :$PORT main:app
