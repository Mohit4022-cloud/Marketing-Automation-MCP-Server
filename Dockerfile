FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir jupyter notebook redis gunicorn

RUN mkdir -p /app/data /app/reports /app/logs /app/output

ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["python3", "-m", "src.server"]
