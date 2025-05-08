#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]; then
  if [ -d "venv" ]; then
    . venv/bin/activate
  else
    read -p "Virtual environment not detected. Continue with installation? (y/N) " choice
    case $choice in
      [yY])
        break
        ;;
      *)
        exit 0
        ;;
    esac
  fi
else
  echo "Virtual environment is active: $VIRTUAL_ENV"
fi

pip install -r requirements.txt
mkdir files db
python manage.py makemigrations accounts
python manage.py makemigrations withings
python manage.py migrate

