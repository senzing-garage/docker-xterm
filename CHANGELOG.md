# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
[markdownlint](https://dlaa.me/markdownlint/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

-

## [1.4.1] - 2022-08-29

### Changed in 1.4.1

- Fix required by `Flask-SocketIO==5.3.0`

## [1.4.0] - 2022-08-24

### Changed in 1.4.0

- removed psutils and duplicate packages from requirements.txt
- update to use `senzingapi-tools`

## [1.3.2] - 2022-06-10

### Changed in 1.3.2

- Ignore "UTF-8" errors output from container
- In `Dockerfile` add "LANG` and `LC_CTYPE`

## [1.3.1] - 2022-06-08

### Changed in 1.3.1

- Upgrade `Dockerfile` to `FROM debian:11.3-slim@sha256:06a93cbdd49a265795ef7b24fe374fee670148a7973190fb798e43b3cf7c5d0f`

## [1.3.0] - 2022-05-19

### Changed in 1.3.0

- Restarts on `exit`
- Added Pylint checks
- Supports Senzing data 3.x
- Updated Docker base to `debian:11.3-slim@sha256:fbaacd55d14bd0ae0c0441c2347217da77ad83c517054623357d1f9d07f79f5e`

## [1.2.8] - 2022-05-04

### Changed in 1.2.8

- Last version supporting Senzing data 2.0.0

## [1.2.7] - 2022-05-02

### Changed in 1.2.7

- In Dockerfile. `ENV LC_ALL=C` to `ENV LC_ALL=C.UTF-8`

## [1.2.6] - 2022-04-19

### Changed in 1.2.6

- Updated python dependencies in `requirements.txt`

## [1.2.5] - 2022-03-21

### Changed in 1.2.5

- Support for `libcrypto` and `libssl`

## [1.2.4] - 2022-02-03

### Added in 1.2.4

- Moved to Debian 11.2 base image
- updated tooling
- updated python requirements text
- added env vars to .bashrc

## [1.2.3] - 2021-10-13

### Added in 1.2.3

- Update path to requirements.txt

## [1.2.2] - 2021-10-12

### Added in 1.2.2

- Added new route to application

## [1.2.1] - 2021-10-11

### Added in 1.2.1

- Updated to senzing/senzing-base:1.6.2

## [1.2.0] - 2021-08-27

### Added to 1.2.0

- Remove static javascript libraries
- Update versions of dependencies (requirements.txt and package.json)

## [1.1.3] - 2021-07-23

### Added to 1.1.3

- Updated to newer version of fio
- Removed duplicate apt package installs

## [1.1.2] - 2021-07-15

### Added in 1.1.2

- Updated to senzing/senzing-base:1.6.1

## [1.1.1] - 2021-07-13

### Added in 1.1.1

- Updated to senzing/senzing-base:1.6.0

## [1.1.0] - 2021-03-03

### Added in 1.1.0

- Added support for `SENZING_BASE_URL_XTERM`

## [1.0.5] - 2021-02-04

### Changed in 1.0.5

- Update to senzing/senzing-base:1.5.5
- Removed `psycopg2-binary`
- Added `libpq-dev` and `python-dev` packages.

## [1.0.4] - 2021-02-04

### Added to 1.0.4

- Added `psycopg2` and `psycopg2-binary` packages.

## [1.0.3] - 2020-07-07

### Changed in 1.0.3

- Update to senzing/senzing-base:1.5.1

## [1.0.2] - 2020-04-30

### Changed in 1.0.2

- Fixed `.gitignore` issue.

## [1.0.1] - 2020-04-27

### Added to 1.0.1

- Added `ODBCSYSINI` and `SENZING_CONFIG_FILE` environment variables

## [1.0.0] - 2020-04-26

### Added to 1.0.0

- Initial X-Term functionality
