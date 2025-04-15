FROM python:3.12-slim
WORKDIR /app
COPY ./src /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
EXPOSE 7777
#CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:7777"]
CMD ["python", "start.py"]