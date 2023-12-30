FROM python:3.9

WORKDIR /app

COPY ./webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../.env .
COPY ./webapp/ .

CMD ["python", "app.py"]