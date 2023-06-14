FROM python:3.9-slim-buster as development

RUN mkdir /cadet
WORKDIR /cadet

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY app app
COPY migrations migrations
COPY cadet.py config.py .flaskenv .
RUN flask db upgrade

EXPOSE 5000
CMD ["flask", "run"]



FROM python:3.9-slim-buster

RUN apt-get update

RUN adduser --system --group --uid 2000 cadet

RUN mkdir /cadet
RUN mkdir /cadet/instance

WORKDIR /cadet

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn

COPY app app
COPY migrations migrations
COPY cadet.py config.py boot-webapp.sh ./
COPY instance_config.py instance/config.py
RUN chmod +x boot-webapp.sh

ENV FLASK_APP cadet.py
ENV SCRIPT_NAME /cadet
ENV APP_CONFIG_CLASS config.ProductionConfig

RUN chown -R cadet:cadet ./
USER cadet

EXPOSE 5500
ENTRYPOINT ["./boot-webapp.sh"]
