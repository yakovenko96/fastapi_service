FROM python:3.12-slim

RUN mkdir /short_links

WORKDIR /short_links

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["sh", "/short_links/docker/app.sh"]
# CMD gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000