FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1
ENV TZ=Canada/Eastern

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["python", "main.py"]
