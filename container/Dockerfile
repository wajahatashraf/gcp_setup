FROM selenium/standalone-chrome:latest

WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app and tests
COPY main.py .
COPY tests ./tests
COPY gcp_created_resources.json /app/gcp_created_resources.json

# Make sure /app is writable by seluser
USER root
RUN chown -R seluser:seluser /app
USER seluser

ENV PORT 8080
EXPOSE 8080

# Run Flask app (Cloud Run requires listening on $PORT)
CMD exec gunicorn --bind :$PORT main:app
