FROM python:3.9-buster
ENV PYTHONUNBUFFERED 1


WORKDIR /Zuthaka
COPY . .

ARG DJANGO_ALLOWED_HOSTS
ARG DJANGO_SECRET_KEY
ARG DJANGO_CORS_ORIGIN_WHITELIST

ENV DJANGO_ALLOWED_HOSTS $DJANGO_ALLOWED_HOSTS
ENV DJANGO_SECRET_KEY $DJANGO_SECRET_KEY
ENV DJANGO_CORS_ORIGIN_WHITELIST $DJANGO_CORS_ORIGIN_WHITELIST

#RUN apt-get update && apt-get install gcc vim apt-utils -y  && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install gcc vim -y  && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip

# Added sudo 
RUN apt-get update && apt-get install sudo
RUN useradd -rm -d /home/pucara -s /bin/bash -g root -G sudo pucara
RUN passwd -d pucara

RUN chown -R pucara /Zuthaka
USER pucara
ENV PATH="${PATH}:/home/pucara/.local/bin"

COPY .devcontainer/rc_files/.bashrc /home/pucara/

WORKDIR /Zuthaka/src
RUN pip3 install --no-cache-dir  -r requirements.txt 

WORKDIR /Zuthaka/src/zuthaka
RUN mkdir Data; exit 0
# RUN python manage.py runscript reset_loaded_db
RUN ./reset_db.sh
RUN python manage.py collectstatic

USER root
RUN echo 'pucara ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
# RUN myuser ALL=(ALL) NOPASSWD: ALL
USER pucara

