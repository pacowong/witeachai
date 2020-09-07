#!/bin/bash
export FLASK_APP="flask_chatbot"
#development
export FLASK_ENV=production
export FLASK_DEBUG=0
export FLASK_RUN_PORT=8000
flask run --host=0.0.0.0 --cert=ssl/cert.pem --key=ssl/key.pem

