ARG BASE_IMAGE=senzing/senzingapi-tools:3.3.0
ARG BASE_BUILDER_IMAGE=node:lts-buster-slim

ARG IMAGE_NAME="senzing/xterm"
ARG IMAGE_MAINTAINER="support@senzing.com"
ARG IMAGE_VERSION="1.4.2"

# -----------------------------------------------------------------------------
# Stage: builder
# -----------------------------------------------------------------------------

FROM ${BASE_BUILDER_IMAGE} AS builder

# Set Shell to use for RUN commands in builder step.

ENV REFRESHED_AT=2022-09-27

# Run as "root" for system installation.

USER root

# Set working directory.

WORKDIR /app

# Add `/app/node_modules/.bin` to $PATH

ENV PATH /app/node_modules/.bin:$PATH

# Install and cache app dependencies.

COPY package.json      /app/package.json
COPY package-lock.json /app/package-lock.json

# Build js packages.

RUN npm config set loglevel warn \
 && npm install

# Install packages via apt for building fio.

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
 && apt-get -y install \
      gcc \
      make \
      pkg-config \
      unzip \
      wget \
 && rm -rf /var/lib/apt/lists/*

# Work around until Debian repos catch up to modern versions of fio.

RUN mkdir /tmp/fio \
 && cd /tmp/fio \
 && wget https://github.com/axboe/fio/archive/refs/tags/fio-3.30.zip \
 && unzip fio-3.30.zip \
 && cd fio-fio-3.30/ \
 && ./configure \
 && make \
 && make install \
 && fio --version \
 && cd \
 && rm -rf /tmp/fio

# -----------------------------------------------------------------------------
# Stage: Final
# -----------------------------------------------------------------------------

# Create the runtime image.

FROM ${BASE_IMAGE} AS runner

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

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
 && apt-get -y install \
      elvis-tiny \
      htop \
      iotop \
      jq \
      net-tools \
      openssh-server \
      postgresql-client \
      procps \
      python3-dev \
      python3-pip \
      python3-pyodbc \
      strace \
      tree \
      unzip \
      wget \
      zip \
 && rm -rf /var/lib/apt/lists/*

# Install packages via pip.

COPY requirements.txt .
RUN pip3 install --upgrade pip \
 && pip3 install -r requirements.txt \
 && rm /requirements.txt

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
COPY --from=builder "/usr/local/bin/fio"                                       "/usr/local/bin/fio"

# The port for the Flask is 5000.

EXPOSE 5000

# Make non-root container.

USER 1001

# Runtime environment variables.

ENV LC_CTYPE=C.UTF-8 \
    SENZING_SSHD_SHOW_PERFORMANCE_WARNING=true

# Runtime execution.

WORKDIR /
CMD ["/app/xterm.py"]
