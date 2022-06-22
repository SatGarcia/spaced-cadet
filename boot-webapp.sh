#!/bin/bash
source venv/bin/activate
flask db upgrade
exec gunicorn -b 0.0.0.0:5500 --access-logfile - --error-logfile - cadet:app
