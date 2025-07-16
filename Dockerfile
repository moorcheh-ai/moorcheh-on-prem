# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app
COPY logs/ ./logs
COPY promptrepo/ ./promptrepo

# Expose port
EXPOSE 8000

# Command to run the server
CMD ["python", "-m", "app.server","--docker"]
