import os
from datetime import timedelta
from dotenv import load_dotenv
expire = timedelta(hours=2)
load_dotenv()

class Config:
    """
        Clase para guardar las configuraciones del proyecto
    """
    TESTING = False
    DB_HOST= os.getenv('DB_HOST')
    SECRET_KEY = os.getenv('SECRET_KEY')
    DB_USER = os.getenv("DB_USER")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv('DB_NAME')
    DEBUG = os.getenv('DEBUG')
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    JWT_SECRET_KEY = os.getenv('SECRET_KEY')
    GOOGLE_CLIENT_SECRET=os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    JWT_ACCESS_TOKEN_EXPIRES = expire

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

class DevelopmentConfig(Config):
    DB_HOST = 'localhost'

# class TestingConfig(Config):
#     DB_SERVER = 'localhost'
#     DATABASE_URI = 'sqlite:///:memory:'