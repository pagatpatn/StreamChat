FROM python:3.11-slim

# Install Chrome & ChromeDriver
RUN apt-get update && apt-get install -y \
    chromium chromium-driver wget unzip curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run script
CMD ["python", "app.py"]
