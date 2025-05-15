"""
    File to put the enpoint handle the jwt authentication.
"""
# admin/auth.py
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash, check_password_hash
from extension import db
from admin.models import User, TokenBlocklist

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    current_user
)

auth_blueprint = Blueprint("auth", __name__, url_prefix="/auth")

# Registration endpoint (ensure your User model has a 'password' field or related setup)
@auth_blueprint.route('/register', methods=['POST'])
def register():
    """
        Endpoint to register user
    """
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    if email is None or username is None or password is None or first_name is None or last_name is None:
        return jsonify("Missing required parameter"), 400
    hashed_password = generate_password_hash(password)
    role = data.get('role')
    if role is None:
        role = 'guest'
    if not role.lower() in ['guest', 'admin', 'superadmin']:
        return jsonify("Role not valid"), 422
    
    user = User(username=username, email=email, first_name=first_name,
                last_name=last_name, password=hashed_password)
    db.session.add(user)
    db.session.commit()
    return jsonify(message="User created successfully"), 201

# Login endpoint: issues access and refresh tokens
@auth_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if username is None or password is None:
        return jsonify("Missing required parameter"), 400
    user = User.query.filter(
        or_(
            func.lower(User.username) == str(username).lower(),
            func.lower(User.email) == str(username).lower(),
        )
        ).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify(message="Invalid credentials"), 401
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 200

# Refresh endpoint: issues a new access token, using the provided refresh token
@auth_blueprint.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
        Refresh token, with the flag refresh true, accept only the refresh token to 
        access this view.
    """
    identity = get_jwt_identity()  # returns user's id
    user = User.query.filter_by(id = identity).first()
    # Block the current access token
    jti = get_jwt()['jti']
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()

    # Generate new tokens
    new_access_token = create_access_token(identity=user)
    new_refresh_token = create_refresh_token(identity=user)
    return jsonify(access_token=new_access_token,
                   refresh_token = new_refresh_token), 200

@auth_blueprint.route('/logout', methods=['POST'])
@jwt_required()  # works with access token
def logout():
    """
        Logout endpoint. Save refresh token to tokenblocklist
    """
    jti = get_jwt()["jti"]
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    return jsonify(message="Access token has been revoked"), 200


@auth_blueprint.route('/who-i-am', methods = ['GET'])
@jwt_required()
def authenticated():
    """
        Return authenticated user
    """
    user = current_user
    return jsonify(user.to_dict())