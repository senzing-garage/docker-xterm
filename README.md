# docker-xterm

## Synopsis

A docker container that gives a web-based terminal.
Similar to `ssh`, but over HTTP/S.

## Overview

The `senzing/xterm` container is a web application that creates the facade of a Xterm window.
Behind the scenes, keystrokes typed into the web-based Xterm window are sent via socket to the running docker container
to be executed within the container.  The results of the command are sent via socket back to the web Xterm window.

Senzing commands such as `G2Command.py`, `G2Explorer.py`, etc. can be executed in Xterm.

To access files outside of the container, files should be place on volumes mounted to docker container.

### Contents

1. [Expectations](#expectations)
1. [Use](#use)
1. [Related artifacts](#related-artifacts)
1. [References](#references)
1. [License](#license)

## Expectations

- **Space:** This repository and demonstration require 6 GB free disk space.
- **Time:** Budget 20 minutes to get the demonstration up-and-running, depending on CPU and network speeds.
- **Background knowledge:** This repository assumes a working knowledge of:
  - [Docker](https://github.com/Senzing/knowledge-base/blob/main/WHATIS/docker.md)

## Use

### Prerequisites

1. [docker](https://github.com/Senzing/knowledge-base/blob/main/HOWTO/install-docker.md)

### Run Docker container

1. :pencil2: Identify a port to view XTerm.
   Example:

    ```console
    export SENZING_XTERM_PORT=8254
    ```

1. Run Docker container.
   Example:

    ```console
    sudo docker run \
      --rm \
      --publish ${SENZING_XTERM_PORT}:5000 \
      senzing/xterm
    ```

### View XTerm

The web-based Senzing X-term can be used to run Senzing command-line programs.

1. If `SENZING_XTERM_PORT` was set to `8254`,
   Senzing X-term will be viewable at
   [localhost:8254](http://localhost:8254).

1. In general, visit the web address having the following format:
   `http://${SENZING_XTERM_HOST}:${SENZING_XTERM_PORT}`
   Example:

    ```console
    export SENZING_XTERM_HOST=localhost
    export SENZING_XTERM_PORT=8254
    ```

   becomes `http://localhost:8254`.

1. See
   [additional tips](https://github.com/Senzing/knowledge-base/blob/main/lists/docker-compose-demo-tips.md#senzing-x-term)
   for working with Senzing X-Term.

## Related artifacts

1. [DockerHub](https://hub.docker.com/r/senzing/xterm)
1. [Helm Chart](https://github.com/Senzing/charts/tree/main/charts/xterm)

## References

- [Development](docs/development.md)
- [Errors](docs/errors.md)
- [Examples](docs/examples.md)

## License

View
[license information](https://senzing.com/end-user-license-agreement/)
for the software container in this Docker image.
Note that this license does not permit further distribution.

This Docker image may also contain software from the
[Senzing GitHub community](https://github.com/Senzing/)
under the
[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

Further, as with all Docker images,
this likely also contains other software which may be under other licenses
(such as Bash, etc. from the base distribution,
along with any direct or indirect dependencies of the primary software being contained).

As for any pre-built image usage,
it is the image user's responsibility to ensure that any use of this image complies
with any relevant licenses for all software contained within.
