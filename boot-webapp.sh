#!/bin/bash
source venv/bin/activate

export SCRIPT_NAME=/cadet
exec gunicorn -b 0.0.0.0:5000 --access-logfile - --error-logfile - cadet:app
