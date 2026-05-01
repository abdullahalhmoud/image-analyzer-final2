FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    steghide \
    libimage-exiftool-perl \
    tesseract-ocr \
    poppler-utils \
    binwalk \
    ruby \
    ruby-dev \
    build-essential \
    && gem install zsteg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

COPY . .

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
