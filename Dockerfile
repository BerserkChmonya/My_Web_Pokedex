FROM python:3.12.2

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

RUN pip3 install python-jose

RUN pip install bcrypt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
