ARG BASE_IMAGE=senzing/senzingapi-tools:3.13.0@sha256:9ed9399ffa9003e9e32f94b26cc46a46d629efaec60457f60be8a5109eb9c9cb
ARG BASE_BUILDER_IMAGE=node:lts-bookworm-slim@sha256:0f2d677a7152ee7ac390837bd4fc36aca12f595411df5d4209f972660e34a7b6

ARG IMAGE_NAME="senzing/xterm"
ARG IMAGE_MAINTAINER="support@senzing.com"
ARG IMAGE_VERSION="1.4.17"

# -----------------------------------------------------------------------------
# Stage: builder
# -----------------------------------------------------------------------------

FROM ${BASE_BUILDER_IMAGE} AS builder

# Set Shell to use for RUN commands in builder step.

ENV REFRESHED_AT=2025-02-03

# Run as "root" for system installation.

USER root

# Set working directory.

WORKDIR /app

# Add `/app/node_modules/.bin` to $PATH

ENV PATH=/app/node_modules/.bin:$PATH

# Install and cache app dependencies.

COPY package.json      /app/package.json
COPY package-lock.json /app/package-lock.json

# Build js packages.

RUN npm config set loglevel warn \
 && npm install

# -----------------------------------------------------------------------------
# Stage: python
# -----------------------------------------------------------------------------

# Create the runtime image.

FROM ${BASE_IMAGE} AS python

# Run as "root" for system installation.

USER root

# Install packages via apt.

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get -y --no-install-recommends install \
      python3 \
      python3-venv \
 && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment.

RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install packages via PIP.

COPY requirements.txt .
RUN pip3 install --upgrade pip \
 && pip3 install -r requirements.txt \
 && rm requirements.txt

# -----------------------------------------------------------------------------
# Stage: Final
# -----------------------------------------------------------------------------

# Create the runtime image.

FROM ${BASE_IMAGE} AS runner

ENV REFRESHED_AT=2025-02-03

ARG IMAGE_NAME
ARG IMAGE_MAINTAINER
ARG IMAGE_VERSION

LABEL Name=${IMAGE_NAME} \
      Maintainer=${IMAGE_MAINTAINER} \
      Version=${IMAGE_VERSION}

# Define health check.

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Install packages via apt.

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get -y --no-install-recommends install \
      fio \
      htop \
      iotop \
      jq \
      net-tools \
      openssh-server \
      postgresql-client \
      procps \
      python3-dev \
      python3-pyodbc \
      strace \
      tree \
      unzip \
      wget \
      zip \
 && rm -rf /var/lib/apt/lists/*

# Copy files from repository.

COPY ./rootfs /

# Copy files from prior stages.

COPY --from=builder "/app/node_modules/socket.io-client/dist/socket.io.js"     "/app/static/js/"
COPY --from=builder "/app/node_modules/socket.io-client/dist/socket.io.js.map" "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-attach/lib/*"               "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-fit/lib/*"                  "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-search/lib/*"               "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-web-links/lib/*"            "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm/css/xterm.css"                    "/app/static/css/"
COPY --from=builder "/app/node_modules/xterm/lib/*"                            "/app/static/js/"
COPY --from=python  "/app/venv"                                                "/app/venv"

# The port for the Flask is 5000.

EXPOSE 5000

# Make non-root container.

USER 1001

# Activate virtual environment.

ENV VIRTUAL_ENV=/app/venv
ENV PATH="/app/venv/bin:${PATH}"

# Runtime environment variables.

ENV LC_CTYPE=C.UTF-8 \
    SENZING_SSHD_SHOW_PERFORMANCE_WARNING=true

# Runtime execution.

WORKDIR /
CMD ["/app/xterm.py"]
