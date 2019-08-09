FROM alpine:latest

USER root

RUN apk update
RUN apk upgrade
RUN apk add bash curl shadow
RUN apk -U add findutils

RUN useradd -ms /bin/bash solc_user
USER solc_user
WORKDIR /home/solc_user

COPY --chown=solc_user solc-select /home/solc_user/solc-select

RUN /home/solc_user/solc-select/scripts/install.sh

ENV  PATH=/home/solc_user/.solc-select:${PATH}

COPY --chown=solc_user test.sh /home/solc_user/test.sh
RUN chmod +x /home/solc_user/test.sh

ENTRYPOINT ["bash", "/home/solc_user/test.sh"]
