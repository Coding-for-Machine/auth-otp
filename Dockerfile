FROM python:3.13.9-alpine3.22

# Set work directory
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .


EXPOSE 8080

CMD ["python", "bot/main.py"]