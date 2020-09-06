FROM python:3.7-stretch

ENV LANG C.UTF-8

RUN apt-get update -qq && apt-get install -qqy --no-install-recommends \
     openssh-client \
     python3-pip \
     python3-setuptools \
     python3-wheel \
     git \
     build-essential \
     python3-dev

COPY . /srv/

WORKDIR /srv

ARG FASTAPI_ENV
ENV FASTAPI_ENV=${FASTAPI_ENV}

RUN pip3 install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["bash", "./run_app.sh"]
