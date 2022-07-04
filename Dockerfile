FROM python:3.9-slim-buster
ENV PYTHONUNBUFFERED 1


WORKDIR /Zuthaka
COPY ./src .

ARG DJANGO_ALLOWED_HOSTS
ARG DJANGO_SECRET_KEY
ARG DJANGO_CORS_ORIGIN_WHITELIST

ENV DJANGO_ALLOWED_HOSTS $DJANGO_ALLOWED_HOSTS
ENV DJANGO_SECRET_KEY $DJANGO_SECRET_KEY
ENV DJANGO_CORS_ORIGIN_WHITELIST $DJANGO_CORS_ORIGIN_WHITELIST

WORKDIR /Zuthaka/
RUN apt-get update && apt-get install gcc vim apt-utils -y  && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip

RUN useradd -ms /bin/bash pucara 
RUN chown -R pucara /Zuthaka
USER pucara
ENV PATH="${PATH}:/home/pucara/.local/bin"

RUN pip3 install --no-cache-dir  -r requirements.txt 

WORKDIR /Zuthaka/zuthaka
RUN python manage.py runscript reset_loaded_db
RUN python manage.py collectstatic

RUN ln -sf /dev/stdout /Zuthaka/zuthaka/zuthaka.log \
    && ln -sf /dev/stderr /Zuthaka/zuthaka/zuthaka.log