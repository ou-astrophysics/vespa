FROM python:3.8

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    netcat-traditional \
    postgresql-client \
  && rm -rf /var/lib/apt/lists/*

RUN pip install \
  pipenv

WORKDIR /usr/src/app

COPY Pipfile ./
COPY Pipfile.lock ./

RUN pipenv install --system --dev

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

USER nobody:nogroup

CMD ["bash", "start_server.sh"]
