FROM rockylinux:9 as build
RUN dnf update -y && && dnf install -y python3
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY manage.py accounts/ templates/ withings/ withings_server/ ./
RUN mkdir files db && python manage.py makemigrations accounts && python manage.py makemigrations withings && python manage.py migrate

FROM build
COPY --from=build manage.py accounts/ templates/ withings/ withings_server/ files/ venv/ db.sqlite3 ./
ENV PATH="/venv/bin:$PATH"
CMD ["gunicorn", "withings_server.wsgi:application", "--name", "withings", "--workers", "3", "--bind=127.0.0.1:8000", "--log-level=info"]
