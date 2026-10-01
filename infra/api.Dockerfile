FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY pipelines pipelines
COPY ml ml
COPY warehouse warehouse
COPY apps/api apps/api
COPY scripts scripts
RUN pip install --no-cache-dir .
RUN useradd -m -u 10001 platform
USER platform
EXPOSE 8000
CMD ["uvicorn","pakdata.main:app","--host","0.0.0.0","--port","8000"]
