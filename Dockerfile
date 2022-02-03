ARG BASE_IMAGE=debian:11.2-slim@sha256:4c25ffa6ef572cf0d57da8c634769a08ae94529f7de5be5587ec8ce7b9b50f9c
ARG BASE_BUILDER_IMAGE=node:lts-buster-slim

# -----------------------------------------------------------------------------
# Stage: builder
# -----------------------------------------------------------------------------

FROM ${BASE_BUILDER_IMAGE} as builder

# Set Shell to use for RUN commands in builder step.

ENV REFRESHED_AT=2022-01-06

LABEL Name="senzing/xterm-builder" \
      Maintainer="support@senzing.com" \
      Version="1.2.3"

# Build arguments.

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

RUN apt-get update \
 && apt-get -y install \
      gcc \
      make \
      unzip \
      wget \
      && rm -rf /var/lib/apt/lists/*

# Work around until Debian repos catch up to modern versions of fio.

RUN mkdir /tmp/fio \
 && cd /tmp/fio \
 && wget https://github.com/axboe/fio/archive/refs/tags/fio-3.27.zip \
 && unzip fio-3.27.zip \
 && cd fio-fio-3.27/ \
 && ./configure \
 && make \
 && make install \
 && fio --version \
 && cd \
 && rm -rf /tmp/fio

# -----------------------------------------------------------------------------
# Stage: Final
# -----------------------------------------------------------------------------

FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2022-01-06

LABEL Name="senzing/xterm" \
      Maintainer="support@senzing.com" \
      Version="1.2.1"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Install packages via apt.

RUN apt-get update \
 && apt-get -y install \
      curl \
      htop \
      iotop \
      jq \
      less \
      libpq-dev \
      net-tools \
      odbcinst \
      openssh-server \
      postgresql-client \
      procps \
      python3-dev \
      python3-pip \
      sqlite3 \
      strace \
      tree \
      unixodbc-dev \
      unzip \
      elvis-tiny \
      wget \
      zip \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder "/usr/local/bin/fio" "/usr/local/bin/fio"

# Install packages via pip.

COPY requirements.txt ./
RUN pip3 install --upgrade pip \
 && pip3 install -r requirements.txt \
 && rm requirements.txt

# The port for the Flask is 5000.

EXPOSE 5000

# Copy files from repository.

COPY ./rootfs /

# Copy files from builder step.

COPY --from=builder "/app/node_modules/xterm/css/xterm.css"                    "/app/static/css/"
COPY --from=builder "/app/node_modules/xterm/lib/*"                            "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-attach/lib/*"               "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-fit/lib/*"                  "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-search/lib/*"               "/app/static/js/"
COPY --from=builder "/app/node_modules/xterm-addon-web-links/lib/*"            "/app/static/js/"
COPY --from=builder "/app/node_modules/socket.io-client/dist/socket.io.js"     "/app/static/js/"
COPY --from=builder "/app/node_modules/socket.io-client/dist/socket.io.js.map" "/app/static/js/"

# Make a simple prompt.

RUN echo " PS1='$ '" >> /etc/bash.bashrc \
 && echo "export TERM=xterm" >> /etc/bash.bashrc \
 && echo "export LC_ALL=C" >> /etc/bash.bashrc \
 && echo "export LANGUAGE=C" >> /etc/bash.bashrc

# Make non-root container.

USER 1001

# Runtime execution.

WORKDIR /
CMD ["/app/xterm.py"]
