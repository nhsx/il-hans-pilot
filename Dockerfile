FROM python:3.10-slim-buster as build

EXPOSE 8000

ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000

RUN pip install --no-cache-dir --upgrade pip
RUN pip install gunicorn==20.1.0

COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

WORKDIR /app
COPY management_interface /app

FROM build AS dev

# This is the stage which docker-compose launches for you.
# It doesn't specify a CMD; that's overridden in
# docker-compose.yml.

# build-essential gives us make, among other niceties.
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y build-essential

FROM build AS prod

# This is the production stage; we don't have nonessential
# apt packages in this stage.

# Reset our WORKDIR because the outer directory isn't needed
WORKDIR /app/management_interface

# See bin/serve for some (quite involved) gunicorn settings.
CMD ["bin/serve"]