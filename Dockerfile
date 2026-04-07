# pull the official docker image
FROM python:3.11.3-slim

# install PDM
RUN pip install -U pip setuptools wheel && \
    pip install pdm

WORKDIR /project

# copy dependency files first for better layer caching
COPY pyproject.toml pdm.lock README.md ./

# install dependencies (this layer is cached unless lock file changes)
RUN pdm install --no-self

# copy the rest of the source code
COPY . .

RUN chmod +x /project/docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/project/docker-entrypoint.sh"]
CMD ["pdm", "run", "start"]
