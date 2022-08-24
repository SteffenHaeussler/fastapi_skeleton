FROM python:3.10-slim

ENV LANG C.UTF-8

ARG FASTAPI_ENV
ENV FASTAPI_ENV=${FASTAPI_ENV} \
     PYTHONFAULTHANDLER=1 \
     PYTHONUNBUFFERED=1 \
     PYTHONHASHSEED=random \
     PIP_NO_CACHE_DIR=off \
     PIP_DISABLE_PIP_VERSION_CHECK=on \
     PIP_DEFAULT_TIMEOUT=100 \
     POETRY_VERSION=1.1.15


RUN apt-get update -qq && apt-get install -qqy --no-install-recommends \
     openssh-client \
     python3-pip \
     python3-setuptools \
     python3-wheel \
     git \
     build-essential \
     python3-dev

RUN pip install "poetry==$POETRY_VERSION"
WORKDIR /app
COPY poetry.lock pyproject.toml /app/

RUN poetry config virtualenvs.create false \
     && poetry install $(test "$YOUR_ENV" == production && echo "--no-dev") --no-interaction --no-ansi

COPY . /app

EXPOSE 5000

ENTRYPOINT ["bash", "./run_app.sh"]

