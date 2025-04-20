#!/bin/bash
export FLASK_APP=main.py
export FLASK_ENV=development
python3 -m flask run --host=0.0.0.0 --port=8000
