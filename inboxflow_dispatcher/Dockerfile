FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
COPY . .
RUN apt-get update && apt-get install -y libpq-dev && \
    pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt
CMD ["python", "dispatcher.py"]
