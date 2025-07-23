# Flask Books & Authors API

This repository hosts a robust Flask API for managing books and authors, featuring advanced security measures and flexible Kubernetes deployment strategies.

## Table of Contents

-   [Features](#features)
-   [Security Enhancements](#security-enhancements)
    -   [JWT Authentication](#jwt-authentication)
    -   [OAuth2 Integration with Google](#oauth2-integration-with-google)
    -   [Rate Limiting with Flask-Limiter](#rate-limiting-with-flask-limiter)
    -   [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
-   [API Endpoints](#api-endpoints)
-   [Kubernetes Deployment](#kubernetes-deployment)
    -   [1. Simple PostgreSQL Deployment with Persistent Volume](#1-simple-postgresql-deployment-with-persistent-volume)
    -   [2. PostgreSQL High Availability with Zalando Operator](#2-postgresql-high-availability-with-zalando-operator)
    -   [3. PostgreSQL High Availability with CloudNativePG Operator](#3-postgresql-high-availability-with-cloudnativepg-operator)

## Features

* **CRUD Operations:** Full C.R.U.D. (Create, Read, Update, Delete) functionality for managing books and authors.
* **User Authentication:** Secure user authentication using JWT (JSON Web Tokens).
* **Social Login:** Seamless user login via Google OAuth2.
* **Rate Limiting:** Protects against abuse and ensures API stability.
* **Role-Based Authorization:** Restricts access to certain API endpoints based on user roles (Guest, Admin, Superadmin).
* **Database Management:** Utilizes SQLAlchemy for ORM and Flask-Migrate for database migrations.

---

## Security Enhancements

This application is built with a strong focus on security, incorporating several key techniques to protect data and control access.

### JWT Authentication

The application leverages **Flask-JWT-Extended** for robust token-based authentication. The `JWTManager` is initialized in `extension.py`, and custom callbacks are registered in `app.py` to handle user identity and token revocation.

* **Token Generation:** Upon successful login (either via traditional username/password or Google OAuth), the API issues both `access_token` and `refresh_token`.
* **User Identity Management:** A `user_identity_loader` is implemented to embed the user's `id` into the JWT, allowing for easy retrieval of user information from the database using `user_lookup_loader`.

    ```python
    # From app.py
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
    ```

* **Token Revocation (Blocklist):** The `TokenBlocklist` model (defined in `admin/models.py`) and `token_in_blocklist_loader` callback provide a mechanism to revoke JWTs, enhancing security by invalidating tokens upon logout or compromise.

    ```python
    # From admin/models.py
    class TokenBlocklist(db.Model):
        """
            For token unvalidation
        """
        __tablename__ = "token_blocklist"
        __table_args__ = {'schema': 'admin'}
        id = db.Column(db.Integer, primary_key=True)
        jti = db.Column(db.String(36), nullable=False, index=True)
        created_at = db.Column(db.DateTime, default=get_current_time)

    # From app.py
    @jwt_manager.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload: dict) -> bool:
        """
            Expand the jwt_required decorator to check if the token is in the block list
        """
        jti = jwt_payload["jti"]
        token = TokenBlocklist.query.filter_by(jti = jti).first()
        return token is not None # True means that is not revoked yet
    ```

### OAuth2 Integration with Google

For a streamlined user experience, the application integrates **Authlib** for Google OAuth2 login. The `OAuth` object is initialized and Google is registered as a client in `app.py`.

* **Simplified Onboarding:** Users can easily sign up and log in using their existing Google accounts, reducing friction.
* **Secure User Information:** User details (email, name) are securely retrieved from Google after successful authentication.
* **Automatic User Provisioning:** If a Google-authenticated user doesn't exist in the database, a new user account is automatically created, associating their Google information. JWTs are then issued for these users, consistent with the application's authentication flow.

    ```python
    # From app.py init_extensions function
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_kwargs={'scope': 'openid email profile'},  # Required by Google
        server_metadata_url='[https://accounts.google.com/.well-known/openid-configuration](https://accounts.google.com/.well-known/openid-configuration)'
    )
    app.oauth = oauth   # Attach OAuth to the app context

    # From admin/routes/router_auth.py
    @auth_blueprint.route('/login/google', methods = ['GET'])
    def google_login():
        google = current_app.oauth.google
        redirect_uri = url_for('auth.google_auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    @auth_blueprint.route('/authorize/google')
    def google_auth():
        google = current_app.oauth.google
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        email = user_info.get("email")
        name = user_info.get("name")
        last_name = user_info.get('family_name')

        user = User.query.filter(func.lower(User.email) == str(email).lower(),).first()
        if not user:
            user = User(
                email=email,
                username=email.split('@')[0],
                first_name=name,
                last_name=last_name,
                password=None
            )
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)

        return jsonify(
            message="Logged in with Google",
            access_token=access_token,
            refresh_token=refresh_token
        )
    ```

### Rate Limiting with Flask-Limiter

To prevent brute-force attacks and ensure fair usage of the API, **Flask-Limiter** is implemented. The `Limiter` is initialized in `extension.py` with a global default limit.

* **Per-Host Rate Limiting:** The `Limiter` is configured with `key_func=get_remote_address`, meaning requests are limited based on the client's IP address.
* **Default Limit:** A `default_limits=["30 per minute"]` is applied globally, restricting each unique IP address to 30 requests per minute. This helps maintain API stability and prevents resource exhaustion.

    ```python
    # From extension.py
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address,default_limits=["30 per minute"])

    # From app.py init_extensions function
    limiter.init_app(app)
    ```

### Role-Based Access Control (RBAC)

The application implements a granular RBAC system using `UserRoleEnum` (defined in `admin/models.py`) and a custom decorator (`decorator.py`).

* **User Roles:** Users can have one of three distinct roles: `guest`, `admin`, or `superadmin`.

    ```python
    # From admin/models.py
    import enum

    class UserRoleEnum(enum.Enum):
        guest = "guest"
        admin = "admin"
        superadmin = "superadmin"

    class User(db.Model):
        # ...
        role = db.Column(db.Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.guest)
        # ...
    ```

* **`admin_required_post` Decorator:** This custom decorator is used to protect specific API endpoints. It checks the `role` of the `current_user` (obtained from the JWT) and allows access only if the user's role is `admin` or `superadmin`. `GET` requests are generally exempted from this restriction, allowing public viewing of data where appropriate. This ensures that sensitive operations are only performed by authorized personnel.

    ```python
    # From decorator.py
    from flask import jsonify, request
    from functools import wraps
    from flask_jwt_extended import (current_user)
    from admin.models import UserRoleEnum

    def admin_required_post(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            """
                Function to handle authenticated user role admin and superadmin
            """
            user = current_user
            if request.method == 'GET':
                return f(*args, **kwargs)
            if user.role == UserRoleEnum.admin or user.role == UserRoleEnum.superadmin:
                return f(*args, **kwargs)
            return jsonify("Permission Denied! admin only"), 403
        return decorator
    ```
    You'll see this decorator applied to routes in `authors/routes/router_author.py`:
    ```python
    # From authors/routes/router_author.py
    @author_blueprint.route('author', methods = ['GET', 'POST'])
    @jwt_required()
    @admin_required_post # Applied here!
    def handle_authors():
        # ...
    ```

---

## API Endpoints

All API endpoints require authentication via JWT unless otherwise specified. Endpoints marked with **(Admin Required)** necessitate an authenticated user with an `admin` or `superadmin` role for `POST`, `PUT`, and `DELETE` operations. `GET` operations on these routes are typically accessible to any authenticated user.

### Authentication Endpoints (`/auth`)

* **`POST /auth/register`**
    * **Description:** Registers a new user with a username, email, password, first name, and last name. A role can optionally be provided (defaults to `guest`).
    * **Requires:** No authentication.
* **`POST /auth/login`**
    * **Description:** Authenticates a user with a username (or email) and password, returning an `access_token` and `refresh_token` upon successful login.
    * **Requires:** No authentication.
* **`GET /auth/login/google`**
    * **Description:** Initiates the Google OAuth2 login flow, redirecting the user to Google's authentication page.
    * **Requires:** No authentication.
* **`GET /auth/authorize/google`**
    * **Description:** Callback endpoint for Google OAuth2. Exchanges the authorization code for tokens and user information, then issues application-specific JWTs.
    * **Requires:** No authentication (handled by Google OAuth flow).
* **`POST /auth/refresh`**
    * **Description:** Generates new `access_token` and `refresh_token` using a valid `refresh_token`. The old `refresh_token` is added to the blocklist.
    * **Requires:** Valid `refresh_token`.
* **`POST /auth/logout`**
    * **Description:** Revokes the current `access_token` by adding its JTI to the blocklist, effectively logging out the user.
    * **Requires:** Valid `access_token`.
* **`GET /auth/who-i-am`**
    * **Description:** Returns the details of the currently authenticated user.
    * **Requires:** Valid `access_token`.

### Author & Book Management Endpoints (`/author-books`)

* **`GET /author-books/author`**
    * **Description:** Retrieves a paginated list of authors. Supports optional `page`, `size`, and `search` (by name or biography) query parameters.
    * **Requires:** Valid `access_token`.
* **`POST /author-books/author`**
    * **Description:** Creates a new author.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`GET /author-books/author/<int:author_id>`**
    * **Description:** Retrieves the details of a specific author by ID, including related books.
    * **Requires:** Valid `access_token`.
* **`PUT /author-books/author/<int:author_id>`**
    * **Description:** Updates the details of an existing author by ID.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`DELETE /author-books/author/<int:author_id>`**
    * **Description:** Deletes an author by ID.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`GET /author-books/book`**
    * **Description:** Retrieves a paginated list of books. Supports optional `page`, `size`, and `search` (by title or description) query parameters.
    * **Requires:** Valid `access_token`.
* **`POST /author-books/book`**
    * **Description:** Creates a new book.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`GET /author-books/book/<int:book_id>`**
    * **Description:** Retrieves the details of a specific book by ID, including related authors.
    * **Requires:** Valid `access_token`.
* **`PUT /author-books/book/<int:book_id>`**
    * **Description:** Updates the details of an existing book by ID.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`DELETE /author-books/book/<int:book_id>`**
    * **Description:** Deletes a book by ID.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`GET /author-books/book/<string:slug>`**
    * **Description:** Retrieves the details of a specific book by its slug, including related authors.
    * **Requires:** Valid `access_token`.
* **`PUT /author-books/book/<string:slug>`**
    * **Description:** Updates the details of an existing book by its slug.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`DELETE /author-books/book/<string:slug>`**
    * **Description:** Deletes a book by its slug.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`POST /author-books/`**
    * **Description:** Creates a new relationship between an author and a book using `author_id` and `book_id`.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`PUT /author-books/<int:author_book_id>`**
    * **Description:** Updates an existing author-book relationship by its ID.
    * **Requires:** Valid `access_token` **(Admin Required)**.
* **`DELETE /author-books/<int:author_book_id>`**
    * **Description:** Deletes an author-book relationship by its ID.
    * **Requires:** Valid `access_token` **(Admin Required)**.

---

## Kubernetes Deployment

This application can be deployed on Kubernetes using various strategies for managing its PostgreSQL database.

### 1. Simple PostgreSQL Deployment with Persistent Volume

This approach demonstrates a basic Kubernetes deployment of the Flask application with a single PostgreSQL database instance. The database data is persisted using a Kubernetes Persistent Volume. This setup is ideal for development and testing environments where high availability is not a primary concern.

### 2. PostgreSQL High Availability with Zalando Operator

This section will detail the deployment of a highly available PostgreSQL cluster using the **Zalando PostgreSQL Operator**. This operator automates the management, scaling, and recovery of PostgreSQL instances, providing a robust solution for production environments.

### 3. PostgreSQL High Availability with CloudNativePG Operator

This section will cover the deployment of a highly available PostgreSQL cluster using the **CloudNativePG Operator**. Similar to the Zalando operator, CloudNativePG streamlines the deployment and management of PostgreSQL within Kubernetes, focusing on Cloud Native principles and offering features like backup/restore and disaster recovery.
