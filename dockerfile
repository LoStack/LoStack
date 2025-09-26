# syntax=docker/dockerfile:1.4
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /lostack

RUN apk update && apk add --no-cache \
    git \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openldap-dev \
    cyrus-sasl-dev \
    openssl-dev \
    docker-cli \
    docker-compose \
    make

COPY requirements.txt /lostack

# Install Python Docker dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install docker

# Install Python requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY . /lostack

ENTRYPOINT ["python3", "-u", "run.py"]

# ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "1", "--timeout", "30", "app:create_app"]

# Dev environment stage
FROM builder AS dev-envs

# # Add user
# RUN addgroup -S docker && \
#     adduser -S --shell /bin/bash --ingroup docker 