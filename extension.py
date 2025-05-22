"""
    Save extensions to isolate imports
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
db = SQLAlchemy() # In flask is better to intialize an object and create a factory
jwt_manager = JWTManager()
oauth = OAuth()
limiter = Limiter(key_func=get_remote_address,default_limits=["30 per minute"])