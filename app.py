"""
    Main file to run flask application
"""
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from config import DevelopmentConfig
from extension import db
def create_app():
    """
        Factory to create instance of the app.
    """
    app = Flask(__name__)
    config = DevelopmentConfig() # Because the property is not being execute unless is instance
    app.config.from_object(config)
    db.init_app(app) # Initialize the db with app config
    jwt_manager = JWTManager(app)
    # If you need to register the models
    from admin.models import User, TokenBlocklist
    from authors.models import AuthorBook, Author, Book
    
    @jwt_manager.user_identity_loader
    def user_identity_lookup(user: User):
        """
            Pass the id of the user as sub for jwt body
        """
        return user.id
    
    @jwt_manager.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        """
            Return the user instance that belongs to this claim.
            Load the current_user object of flask with this info.
        """
        identity = jwt_data["sub"]
        return User.query.filter_by(id=identity).one_or_none()
    
    @jwt_manager.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload: dict) -> bool:
        jti = jwt_payload["jti"]
        token = TokenBlocklist.query.filter_by(jti = jti).first()
        return token is not None # True means that is not revoked yet

    # Add my blueprints
    from admin.routes.router_auth import auth_blueprint
    app.register_blueprint(auth_blueprint)

    # register the migrations
    migrate = Migrate(app, db)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))