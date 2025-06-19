FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /uvx /bin/

ARG UID=1000
ARG GID=1000
ARG EXPORT_PATH="/radar/app/static/exports/"
ARG UPLOAD_PATH="/radar/app/static/uploads/"

ENV TZ="Europe/Madrid"\
    APP_VERSION="dev"


#Pilow webp support and locales
RUN apt-get update && \
    apt-get install -y \
    libwebp-dev tzdata \
    procps \
    gcc python3-dev \
    git


RUN groupadd -g "${GID}" python \
    && useradd --create-home --no-log-init -u "${UID}" -g "${GID}" python


RUN mkdir -p ${EXPORT_PATH} && chown python ${EXPORT_PATH}
RUN mkdir -p ${UPLOAD_PATH} && chown python ${UPLOAD_PATH}
RUN mkdir /radar/.logs && chown python /radar/.logs
RUN touch /radar/.logs/radar.log && chown python /radar/.logs/radar.log
RUN touch /radar/.logs/workers.log && chown python /radar/.logs/workers.log


WORKDIR /radar
COPY --chown=python:python ./README.md ./uv.lock ./pyproject.toml ./
RUN uv sync --frozen

COPY --chown=python:python ./app /radar/app
ENV PATH="/radar/.venv/bin:$PATH"

USER python
