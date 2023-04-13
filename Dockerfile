FROM --platform="linux/amd64" public.ecr.aws/docker/library/python:3.10-slim-bullseye AS builder

EXPOSE 80

ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

# Install & Configure Gunicorn
RUN pip install gunicorn==20.1.0
RUN mkdir -p /var/log/gunicorn/
RUN touch /var/log/gunicorn/dev.log

# Configure Nginx
RUN apt-get update
RUN apt-get -y install nginx
COPY hans.site.conf /etc/nginx/sites-available/hans
RUN ln -s /etc/nginx/sites-available/hans /etc/nginx/sites-enabled
RUN rm /etc/nginx/sites-enabled/default


WORKDIR /app
COPY management_interface /app/
