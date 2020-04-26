ARG BASE_IMAGE=senzing/senzing-base:1.4.0
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2020-04-26

LABEL Name="senzing/xterm" \
      Maintainer="support@senzing.com" \
      Version="1.0.0"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Install packages via apt.

RUN apt-get update \
 && apt-get -y install \
    fio \
    htop \
    iotop \
    ipython \
    itop \
    less \
    odbc-postgresql \
    net-tools \
    pstack \
    python-pyodbc \
    unixodbc \
    unixodbc-dev \
    vim \
 && rm -rf /var/lib/apt/lists/*

# Install packages via pip.

RUN pip3 install --upgrade pip \
 && pip3 install \
      click==7.0 \
      csvkit \
      eventlet \
      flask-socketio==3.3.1 \
      flask==1.0.2 \
      fuzzywuzzy \
      itsdangerous==1.1.0 \
      jinja2==2.10 \
      markupsafe==1.1.1 \
      pandas \
      ptable \
      pyodbc \
      pysnooper \
      python-levenshtein \
      python-engineio==3.4.3 \
      python-socketio==3.1.2 \
      setuptools \
      six==1.12.0 \
      werkzeug==0.14.1

# The port for the Flask is 5000.

EXPOSE 5000

# Copy files from repository.

COPY ./rootfs /

# Make a simple prompt.

RUN echo " PS1='$ '" >> /etc/bash.bashrc

# Make non-root container.

USER 1001

# Set environment variables.

ENV PATH=${PATH}:/opt/senzing/g2/python

# Runtime execution.

WORKDIR /app
CMD ["/app/xterm.py"]
