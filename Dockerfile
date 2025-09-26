# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY vtt_multilang_translator.py server.py requirements_api.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements_api.txt -r requirements.txt
ENV PORT=8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
