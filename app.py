"""
    Main file to run flask application
"""
from flask import Flask
from flask_migrate import Migrate
from config import DevelopmentConfig
from extension import (db, jwt_manager, oauth, limiter)
def create_app():
    """
        Factory to create instance of the app.
    """
    app = Flask(__name__)
    config = DevelopmentConfig() # Because the property is not being execute unless is instance
    app.config.from_object(config)
    init_extensions(app)
    # Register models to myapp
    register_models()

    # Add blueprints
    register_blueprints(app)

    # register the migrations
    migrate = Migrate(app, db)
    @app.route('/', methods = ['GET'])
    def index():
        return "Hello world"
    return app

def init_extensions(app):
    """Initialize and configure Flask extensions."""
    # Initialize the database
    db.init_app(app)

    # Setup JWT
    jwt_manager.init_app(app)
    register_jwt_callbacks(jwt_manager)

    # Setup OAuth for Google
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_kwargs={'scope': 'openid email profile'},  # Required by Google
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    )
    app.oauth = oauth  # Attach OAuth to the app context

    # Setup rate limiter
    limiter.init_app(app)

def register_jwt_callbacks(jwt_manager):
    """Register JWT callbacks for user identity and token blocklist management."""
    from admin.models import User, TokenBlocklist

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
        """
            Expand the jwt_required decorator to check if the token is in the block list
        """
        jti = jwt_payload["jti"]
        token = TokenBlocklist.query.filter_by(jti = jti).first()
        return token is not None # True means that is not revoked yet


def register_blueprints(app):
    """Register all blueprints for the app."""
    from admin.routes.router_auth import auth_blueprint
    from authors.routes.router_author import author_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(author_blueprint)
    # Health api
    @app.route('/health',methods = ['GET'])
    def hello():
        print('check')
        return "Hello world"

def register_models():
    """
    Import all models and events so that they are registered with SQLAlchemy.
    This ensures that any module-level code (such as event listener registrations)
    is executed.
    """
    # Import models from admin and authors modules
    from admin.models import User, TokenBlocklist
    from authors.models import AuthorBook, Author, Book
    # Import the events module so its listeners get registered.
    from authors import events

if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))
    