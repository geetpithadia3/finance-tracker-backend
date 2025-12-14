# Python 3.12 Slim
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# Install system dependencies
RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && apt-get clean

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Run entrypoint
COPY scripts/entrypoint.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
