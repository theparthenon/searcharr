FROM python:3.15-slim

LABEL Name=Searcharr

WORKDIR /app
ADD . /app

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "searcharr.py"]
