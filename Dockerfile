FROM python:3.10.8-slim-bullseye

RUN apt update && apt upgrade -y && apt install git -y

WORKDIR /app

COPY requirements.txt .
RUN pip install -U pip && pip install -U -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
