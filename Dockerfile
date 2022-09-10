FROM python:3.9-slim-bullseye as builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update && apt-get install --no-install-recommends -y build-essential libssl-dev libffi-dev libyaml-dev && python -m pip install --upgrade pip

RUN pip install --no-cache-dir cmdserver

FROM python:3.9-slim-bullseye

ENV CMDSERVER_CONFIG_HOME=/config

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
VOLUME ["/config"]

ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update && apt-get install --no-install-recommends -y curl

HEALTHCHECK --interval=10s --timeout=2s \
  CMD curl -f -s --show-error http://localhost:8080/api/1/version || exit 1

EXPOSE 8080

CMD [ "cmdserver" ]