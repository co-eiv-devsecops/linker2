FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HOST=0.0.0.0 \
    PORT=8080 \
    LINKER_DB=/app/data/linker.db

EXPOSE 8080

CMD ["python", "app.py"]
