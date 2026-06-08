FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  netcat-traditional \
  postgresql-client \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --frozen --dev --no-install-project

COPY . .

ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/matplotlib

EXPOSE 8080

USER nobody:nogroup

CMD ["bash", "start_server.sh"]
