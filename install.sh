#!/bin/bash

if [ -n "$VIRTUAL_ENV" ]; then
  echo "Virtual environment is active: $VIRTUAL_ENV"
else
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
fi

pip install -r requirements.txt
mkdir files db
python manage.py makemigrations accounts
python manage.py makemigrations upload
python manage.py migrate
