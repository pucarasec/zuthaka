#!/bin/bash
. ../../../env/bin/activate
rm Data/db.sqlite3
rm backendapi/migrations/*.py
python manage.py makemigrations backendapi
python manage.py migrate
python manage.py loaddata data.json
python manage.py runscript load_modules
