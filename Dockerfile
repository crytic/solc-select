#FROM alpine:latest

# Hack: Extend from the official solc container.
#       We really don't need to extend from this, but
#       it also extends from alpine, and this allows
#       us to have solc-select auto-rebuilt on Dockerhub
#       every time the official solc Docker image is rebuilt.
#       As a bonus, we also get the nightly build of `solc`.
FROM ethereum/solc:nightly-alpine

MAINTAINER Evan Sultanik

USER root

# First, move the preexisting nightly build we inherited from the official image into place:
RUN mv /usr/local/bin/solc /usr/bin/solc-vnightly

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

# Select the latest, non-nightly-build version of solc as the default:
RUN solc-select --list | grep -v nightly | tail -n1 | xargs solc-select

COPY scripts/solc /usr/bin/
COPY scripts/solc-wrapper /usr/bin/
COPY scripts/chroot.sh /usr/bin/

COPY scripts/install.sh /usr/bin/
COPY bin/solc /etc/solc_template
RUN cat /etc/solc_template >> /usr/bin/install.sh
RUN echo EOF >> /usr/bin/install.sh
RUN echo finalize >> /usr/bin/install.sh
RUN rm /etc/solc_template

RUN mkdir -p /workdir

WORKDIR /workdir

ENTRYPOINT ["/usr/bin/solc-wrapper"]
