# backend/app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from models.database import db
from routes.upload import upload_bp
from routes.extract import extract_bp
from routes.batch import batch_bp

import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)
    app.register_blueprint(upload_bp)
    app.register_blueprint(extract_bp)
    app.register_blueprint(batch_bp)

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)