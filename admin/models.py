"""
    Models for the schema admin
"""
import enum
from datetime import datetime, timezone
from extension import db

def get_current_time():
    return datetime.now(tz=timezone.utc)

class UserRoleEnum(enum.Enum):
    guest = "guest"
    admin = "admin"
    superadmin = "superadmin"


class User(db.Model):
    """User model"""
    __tablename__ = 'user'
    __table_args__ = {'schema': 'admin'}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable = False)
    role = db.Column(db.Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.guest)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    country = db.Column(db.String(150), nullable=True)

    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    def __repr__(self):
        return f'<User {self.username}>'
    
    def check_password(self, password):
        """
            check password user, compare the hashed if you want to do it from user model
        """
        return True
        # return compare_digest(password, "password")

    def to_dict(self):
        """
            Convert object to dict
        """
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'email': self.email
        }
    
class TokenBlocklist(db.Model):
    """
        For token unvalidation
    """
    __tablename__ = "token_blocklist"
    __table_args__ = {'schema': 'admin'}
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=get_current_time)

