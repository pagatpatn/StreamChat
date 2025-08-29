FROM python:3.11-slim

# Install Chromium + ChromeDriver + minimal dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium chromium-driver wget unzip curl gnupg2 ca-certificates \
    libnss3 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxi6 libxtst6 libxrandr2 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdbus-1-3 libgtk-3-0 libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables so Selenium knows where Chrome is
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy all files into container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the Python app
CMD ["python", "app.py"]
