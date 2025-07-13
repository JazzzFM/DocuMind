FROM python:3.11-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN apt-get update && apt-get install -y     tesseract-ocr     tesseract-ocr-eng     tesseract-ocr-spa     poppler-utils     && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["python", "documind/manage.py", "runserver", "0.0.0.0:8000"]