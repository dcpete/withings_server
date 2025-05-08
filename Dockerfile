FROM rockylinux:9 as build
RUN dnf update -y && && dnf install -y httpd python3 && mkdir -p /var/www/withings
WORKDIR /var/www/withings
RUN python -m venv venv
ENV PATH="/var/www/withings/venv/bin:$PATH"
COPY install.sh requirements.txt manage.py accounts/ templates/ withings/ withings_server/ ./
RUN chmod +x install.sh && ./install.sh
CMD ["gunicorn", "withings_server.wsgi:application", "--name", "withings", "--workers", "3", "--bind=127.0.0.1:8000", "--log-level=info"]
