FROM python:3
ENV PYTHONUNBUFFERED 1
RUN pip install django
RUN pip install psycopg2

RUN apt update
RUN apt install sudo
RUN apt install -y vim
RUN apt install -y cron
