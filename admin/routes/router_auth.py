"""
    File to put the enpoint handle the jwt authentication.
"""
# admin/auth.py
from flask import Blueprint, request, jsonify, url_for, current_app
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

@auth_blueprint.route('/login/google', methods = ['GET'])
def google_login():
    """
        Endpoint to redirect user to google website to login
    """
    # Redirect user to Google for authorization.
    google = current_app.oauth.google
    redirect_uri = url_for('auth.google_auth', _external=True) # prefix of the blueprint 'auth'
    print('url for google', redirect_uri)
    return google.authorize_redirect(redirect_uri)


@auth_blueprint.route('/authorize/google')
def google_auth():
    # Callback endpoint. This code exchanges the auth code for token and user info.
    google = current_app.oauth.google
    token = google.authorize_access_token()
    user_info = token.get('userinfo')

    # Example: Extract some user data
    email = user_info.get("email")
    name = user_info.get("name")
    last_name = user_info.get('family_name')

    # Now, check if this email already exists in your database
    user = User.query.filter(func.lower(User.email) == str(email).lower(),).first()
    if not user:
        user = User(
            email=email,
            username=email.split('@')[0], # Generate a username with the email
            first_name=name,
            last_name=last_name,
            password=None  # You might leave password empty or set a random placeholder
        )
        db.session.add(user)
        db.session.commit()

    # After logging in via OAuth, issue JWT tokens for consistency
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)

    # You could return tokens, set secure cookies, or redirect to your frontend as needed.
    return jsonify(
        message="Logged in with Google",
        access_token=access_token,
        refresh_token=refresh_token
    )