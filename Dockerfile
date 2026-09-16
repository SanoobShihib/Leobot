FROM python:3.10-slim-bookworm

# Combine apt commands and clean up cache to reduce image size
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements first (takes advantage of Docker caching)
COPY requirements.txt /requirements.txt
RUN pip install -U pip && pip install -U -r /requirements.txt

# Set the working directory (this automatically creates /app and handles the 'cd')
WORKDIR /app

# Copy the rest of your application code
COPY . .

CMD ["python", "bot.py"]
