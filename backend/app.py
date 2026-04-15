# backend/app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from models.database import db
from routes.upload import upload_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)  # Allow React frontend to call this API
    db.init_app(app)

    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()  # Creates tables if they don't exist

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)