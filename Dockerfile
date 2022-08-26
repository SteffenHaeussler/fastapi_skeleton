# syntax=docker/dockerfile:1.2

#############################
# Prepare base environment
# following https://stackoverflow.com/a/57886655
#############################

FROM python:3.10-slim as base

ARG DEBIAN_FRONTEND=noninteractive
ARG FASTAPI_ENV

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV FASTAPI_ENV=${FASTAPI_ENV}

RUN apt-get update && apt-get install -y --no-install-recommends \
     build-essential \
     && rm -rf /var/lib/apt/lists/*

RUN apt-get clean

WORKDIR /app


###########################
# Install Python dependencies
###########################

FROM base as build-image

ENV  PYTHONFAULTHANDLER=1 \
     PYTHONUNBUFFERED=1 \
     PYTHONHASHSEED=random \
     PIP_NO_CACHE_DIR=off \
     PIP_DISABLE_PIP_VERSION_CHECK=on \
     PIP_DEFAULT_TIMEOUT=100 \
     POETRY_VERSION=1.1.15

# RUN apt-get update -qq && apt-get install -qqy --no-install-recommends \
#      openssh-client \
#      python3-pip \
#      python3-setuptools \
#      python3-wheel \
#      python3-dev
# WORKDIR /app

RUN pip install "poetry==$POETRY_VERSION"
# RUN python -m venv /venv
COPY pyproject.toml .
RUN poetry export -o requirements.txt

RUN python -m venv .venv && \
     .venv/bin/pip install -r requirements.txt
# RUN poetry install $(test "$YOUR_ENV" == production && echo "--no-dev") --no-interaction --no-ansi

# COPY . /app
# COPY . .
# RUN . /venv/bin/activate && poetry build

###########################
# Install app dependencies
###########################

FROM base AS build-app

COPY . /app
RUN rm -rf app/tests

# # # ###########################
# # # Prepare runtime environment
# # # ###########################

FROM base AS env

ENV PATH=/app/.venv/bin:$PATH

COPY --from=build-image /app/.venv /app/.venv
COPY --from=build-app /app /app

EXPOSE 5000

ENTRYPOINT ["bash", "./run_app.sh"]

