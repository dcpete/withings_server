#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]; then
  if [ -d ".venv" ]; then
    . .venv/bin/activate
  else
    read -p "Virtual environment not detected. Create one and continue with installation? (y/N) " choice
    case $choice in
      [yY])
        python3 -m venv .venv
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

python3 -m pip install -r requirements.txt
python3 manage.py makemigrations accounts
python3 manage.py makemigrations withings
python3 manage.py migrate
