set FLASK_APP=flask_chatbot
set FLASK_ENV=development
set FLASK_DEBUG=1
flask run --host=0.0.0.0 --cert="ssl/cert.pem" --key="ssl/key.pem"