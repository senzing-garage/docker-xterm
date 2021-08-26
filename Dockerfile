ARG BASE_IMAGE=senzing/senzing-base:1.6.1
ARG BASE_BUILDER_IMAGE=node:lts-buster-slim

# -----------------------------------------------------------------------------
# Stage: builder
# -----------------------------------------------------------------------------

FROM ${BASE_BUILDER_IMAGE} as builder

# Set Shell to use for RUN commands in builder step.

ENV REFRESHED_AT=2021-08-22

LABEL Name="senzing/xterm-builder" \
      Maintainer="support@senzing.com" \
      Version="1.0.0"

# Build arguments.

ARG SENZING_API_SERVER_VERSION=2.7.2

USER root

# Set working directory.

WORKDIR /app

# Add `/app/node_modules/.bin` to $PATH

ENV PATH /app/node_modules/.bin:$PATH

# Install and cache app dependencies.

COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json


RUN npm config set loglevel warn \
 && npm install
