FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

# System deps (curl for health/debug, build tools if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

EXPOSE 8501

# OPENAI_API_KEY must be provided at runtime
ENV OPENAI_MODEL=o3

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]


