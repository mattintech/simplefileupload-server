FROM python:3.13-slim
WORKDIR /app
COPY ./src /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
EXPOSE 7777

# The actual values should be provided when running the container
ENV CLIENT_KEY=default-secret-key \
    UPLOAD_FOLDER=tmp/uploads \
    DEBUG=False

CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:7777"]