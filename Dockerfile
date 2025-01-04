# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKER_TIMEOUT=300 \
    GRACEFUL_TIMEOUT=120 \
    KEEP_ALIVE=120

# Set work directory
WORKDIR /app

# Install system dependencies
        gcc \
        python3-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create a non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "300", "--keep-alive", "120", "--graceful-timeout", "120", "--bind", "0.0.0.0:8000", "app:app"]
