# syntax=docker/dockerfile:1.2

#############################
# Prepare base environment
#############################

FROM python:3.12-slim as base

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
     PIP_NO_CACHE_DIR=off \
     PIP_DISABLE_PIP_VERSION_CHECK=on \
     PIP_DEFAULT_TIMEOUT=100

# RUN apt-get update -qq && apt-get install -qqy --no-install-recommends \
#      python3-dev

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app
RUN uv sync --frozen

###########################
# Install app dependencies
###########################

FROM base AS build-app

COPY . /app
RUN rm -rf app/tests

#############################
# Prepare runtime environment
#############################

FROM base AS env

ENV PATH="/root/.local/bin/:$PATH"

COPY --from=build-image /app/.local /app/.local
COPY --from=build-app /app /app

EXPOSE 5000

ENTRYPOINT ["bash", "./run_app.sh"]

