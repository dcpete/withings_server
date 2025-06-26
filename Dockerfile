FROM rockylinux:9 as build
RUN dnf update -y && dnf install -y httpd python3 && mkdir -p /var/www/withings_server
WORKDIR /var/www/withings_server
VOLUME /var/www/withings_server/files /var/www/withings_server/db
RUN python3 -m venv .venv
ENV PATH="/var/www/withings_server/.venv/bin:$PATH"
ENV DJANGO_SETTINGS_MODULE="withings_server.settings"
COPY requirements.txt manage.py accounts/ templates/ withings/ withings_server/ ./
RUN pip3 install -r requirements.txt
RUN python3 manage.py makemigrations accounts
RUN python3 manage.py makemigrations withings
RUN python3 manage.py migrate
CMD ["gunicorn", "withings_server.wsgi:application", "--name", "withings", "--workers", "3", "--bind=127.0.0.1:8000", "--log-level=info"]
