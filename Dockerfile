# Dockerfile

# pull the official docker image
FROM python:3.11.1-slim AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /project/
COPY . /project/


WORKDIR /project

RUN pdm install
RUN chmod +x docker-entrypoint.sh


EXPOSE 8080
CMD ["pdm", "run", "start"]
