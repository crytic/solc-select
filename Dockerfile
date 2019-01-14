FROM alpine:latest
MAINTAINER Evan Sultanik

USER root

RUN apk update
RUN apk upgrade
RUN apk add bash curl

# Install all versions of solc
COPY scripts/install_solc.sh /
RUN bash /install_solc.sh
RUN rm /install_solc.sh
# Install the solc-selection script:
COPY scripts/solc-select /usr/bin/

# solc-select requires a newer version of `find`:
RUN apk -U add findutils

# Select the latest version of solc as the default:
RUN solc-select --list | tail -n1 | xargs solc-select

COPY scripts/solc /usr/bin/

RUN mkdir -p /workdir

WORKDIR /workdir

ENTRYPOINT ["/usr/bin/solc"]