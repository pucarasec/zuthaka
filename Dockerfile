FROM python:3.9-slim-buster
ENV PYTHONUNBUFFERED 1

WORKDIR /Zuthaka
COPY . ./

ARG DJANGO_ALLOWED_HOSTS
ARG DJANGO_SECRET_KEY
ARG DJANGO_CORS_ORIGIN_WHITELIST

ENV DJANGO_ALLOWED_HOSTS $DJANGO_ALLOWED_HOSTS
ENV DJANGO_SECRET_KEY $DJANGO_SECRET_KEY
ENV DJANGO_CORS_ORIGIN_WHITELIST $DJANGO_CORS_ORIGIN_WHITELIST


WORKDIR /Zuthaka/Zuthaka/django_app
RUN apt update && apt install gcc vim -y  && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir  -r requirements.txt 

WORKDIR /Zuthaka/Zuthaka/django_app/zuthaka
RUN python manage.py makemigrations
RUN python manage.py migrate
RUN python manage.py loaddata data.json
RUN python3 manage.py collectstatic


#CMD ["/bin/bash"]
#CMD ["python","manage.py","runserver"] 
#CMD ["gunicorn","zuthaka.wsgi:application"]
