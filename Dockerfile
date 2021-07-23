ARG BASE_IMAGE=senzing/senzing-base:1.6.1
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2021-07-23

LABEL Name="senzing/xterm" \
      Maintainer="support@senzing.com" \
      Version="1.1.3"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Install packages via apt.

RUN apt-get update \
 && apt-get -y install \
      elfutils \
      htop \
      iotop \
      ipython3 \
      itop \
      less \
      libpq-dev \
      net-tools \
      procps \
      pstack \
      python3-setuptools \
      strace \
      telnet \
      tree \
      unixodbc-dev \
      zip \
      && rm -rf /var/lib/apt/lists/*

# Install packages via pip.

COPY requirements.txt ./
RUN pip3 install --upgrade pip \
 && pip3 install -r requirements.txt

# work around until Debian repos catch up to modern versions of fio --Dr. Ant

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

# The port for the Flask is 5000.

EXPOSE 5000

# Copy files from repository.

COPY ./rootfs /

# Make a simple prompt.

RUN echo " PS1='$ '" >> /etc/bash.bashrc

# Make non-root container.

USER 1001

# Runtime execution.

WORKDIR /
CMD ["/app/xterm.py"]
