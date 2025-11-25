# This image is to start the edge node
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV NODE_ID=""
ENV CENTRAL_URL=""
ENV EDGE_PORT="5000"
ENV EDGE_HOST="0.0.0.0"
ENV LOG_LEVEL="INFO"

ENTRYPOINT ["python3", "edge_main.py"]
CMD ["--node-id", "${NODE_ID}", "--central-url", "${CENTRAL_URL}", "--port", "${EDGE_PORT}", "--host", "${EDGE_HOST}", "--log-level", "${LOG_LEVEL}"]