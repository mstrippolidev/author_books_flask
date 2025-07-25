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
    -   [Docker Image and CI/CD Pipeline](#docker-image-and-ci/cd-pipeline)
    -   [AWS EKS Cluster Architecture](#aws-eks-cluster-architecture)
    -   [1. Simple PostgreSQL Deployment with Persistent Volume](#1-simple-postgresql-deployment-with-persistent-volume)
        -   [PostgreSQL Persistent Volume Claim (PVC)](#postgresql-persistent-volume-claim-pvc)
        -   [PostgreSQL ClusterIP Service](#postgresql-clusterip-service)
        -   [PostgreSQL Deployment](#postgresql-deployment)
        -   [Database Migration Job](#database-migration-job)
        -   [Flask Application ClusterIP Service](#flask-application-clusterip-service)
        -   [Flask Application Deployment](#flask-application-deployment)
    -   [2. PostgreSQL High Availability with Zalando Operator](#2-postgresql-high-availability-with-zalando-operator)
        -   [Installation of Zalando PostgreSQL Operator](#installation-of-zalando-postgresql-operator)
        -   [Deploying the Highly Available PostgreSQL Cluster](#deploying-the-highly-available-postgresql-cluster)
        -   [Verifying Cluster Deployment](#verifying-cluster-deployment)
        -   [Connecting the Flask Application to the Zalando PostgreSQL Cluster](#connecting-the-flask-application-to-the-zalando-postgresql-cluster)
        -   [Benefits of Using Zalando PostgreSQL Operator](#benefits-of-using-zalando-postgresql-operator)
        -   [Further Improvements to the Zalando Operator Manifest](#further-improvements-to-the-zalando-operator-manifest)
     -   [3. PostgreSQL High Availability with CloudNativePG Operator](#3-postgresql-high-availability-with-cloudnativepg-operator)
        -   [Installation of CloudNativePG Operator](#installation-of-cloudnativepg-operator)
        -   [Deploying the CloudNativePG Cluster](#deploying-the-cloudnativepg-cluster)
        -   [Connecting the Flask Application to CloudNativePG](#connecting-the-flask-application-to-cloudnativepg)
        -   [Benefits of Using CloudNativePG Operator](#benefits-of-using-cloudnativepg-operator)
        -   [Further Improvements to the CloudNativePG Manifest](#further-improvements-to-the-cloudnativepg-manifest)
 
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

This application is designed for containerized deployment on Kubernetes, with a focus on modularity and scalability.

### Docker Image and CI/CD Pipeline

The application's Docker image is built using a multi-stage Dockerfile and automatically pushed to Docker Hub via GitHub Actions.

* **Multi-Stage Dockerfile:** The `Dockerfile` employs a multi-stage build pattern to optimize image size and build speed.

    ```dockerfile
    # docker_files/Dockerfile
    # Stage 1: Build Dependencies
    FROM python:3.12-slim as builder
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1
    WORKDIR /dependencies
    COPY ./requirements.txt .
    RUN pip install --upgrade pip && \
        pip install --no-cache-dir --prefix=/dependencies -r requirements.txt

    # Stage 2: Production Image
    FROM python:3.12-slim
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1
    WORKDIR /app
    COPY --from=builder /dependencies /usr/local
    COPY ./ .
    RUN chmod +x /app/entrypoint.sh
    EXPOSE 8000
    ENTRYPOINT ["/app/entrypoint.sh"]
    ```
    This setup ensures that only the necessary runtime components and installed dependencies are included in the final image, reducing its footprint. By copying `requirements.txt` first, Docker can cache the dependency installation step, significantly speeding up subsequent builds if dependencies haven't changed.

* **GitHub Actions CI/CD:** A GitHub Actions workflow (`.github/workflows/pipeline_docker.yml`) automates the process of building and pushing new Docker images to Docker Hub whenever changes are pushed to the `main` branch.

    ```yaml
    # .GitHub/workflows/pipeline_docker.yml
    name: Docker push job
    on:
      push:
        branches:
          - main
    jobs:
      run-test:
        runs-on: ubuntu-latest
        environment: MAIN
        steps:
          - name: run test
            run: echo "running test (checkout and run test to db test)"
          - name: check values
            run: echo ${{ secrets.DOCKER_USERNAME }}

      build-push-docker-image:
        runs-on: ubuntu-latest
        environment: MAIN
        needs: [run-test]
        steps:
          - name: checkout code
            uses: actions/checkout@v4
            with:
              fetch-depth: 0
          - name: Login to Docker Hub
            uses: docker/login-action@v3
            with:
              username: ${{ secrets.DOCKER_USERNAME }}
              password: ${{ secrets.DOCKER_PASSWORD }}
          - name: Set up QEMU
            uses: docker/setup-qemu-action@v3
          - name: Set up Docker Buildx
            uses: docker/setup-buildx-action@v3
          - name: Build and push
            uses: docker/build-push-action@v6
            with:
              context: .
              file: docker_files/Dockerfile
              push: true
              tags: |
                ${{ secrets.DOCKER_USERNAME }}/flask_app_distributed:latest
                ${{ secrets.DOCKER_USERNAME }}/flask_app_distributed:${{ github.sha }}
          - name: Log out from Docker Hub
            run: docker logout
    ```
    This workflow ensures that the Docker image is always up-to-date with the latest codebase, ready for deployment. It includes steps for logging into Docker Hub, setting up QEMU and Buildx for multi-platform builds, and finally building and pushing the image with `latest` and `commit-SHA` tags.

### AWS EKS Cluster Architecture

The application is deployed on an **Amazon EKS (Elastic Kubernetes Service)** cluster. The cluster's networking is configured across three Availability Zones (AZs) with a total of six subnets: three public and three private.

To ensure optimal resource allocation and security, the EKS cluster utilizes two distinct node groups:

* **`role=app` Node Group:** Nodes in this group are dedicated to running the Flask application pods. These nodes are deployed in private subnets across AZ B and C. This allows the application pods to remain isolated from direct internet access, enhancing security. Traffic to the application is exposed via a public AWS Load Balancer (configured separately, typically via an Ingress Controller not shown in these basic manifests).
* **`role=db` Node Group:** Nodes in this group are reserved for database-related pods (like PostgreSQL). This specific node group is isolated in a private subnet within AZ A. This separation ensures that sensitive database workloads run on dedicated infrastructure, minimizing interference and potentially allowing for different instance types or security configurations.

This architecture offers flexibility. While the current setup uses private subnets for application and database nodes, users can adapt the configuration to their needs, such as:
* Deploying entirely within public subnets for simpler setups.
* Using private subnets with an Internet Gateway for "egress-only" architecture, allowing outbound traffic from pods but preventing direct inbound public access to the nodes.

### 1. Simple PostgreSQL Deployment with Persistent Volume

This section details the Kubernetes manifests for a basic, single-instance PostgreSQL deployment, suitable for development or demonstration purposes, along with the Flask application components.

#### PostgreSQL Persistent Volume Claim (PVC)

The `postgres-pvc.yml` manifest declares a `PersistentVolumeClaim` (PVC), which requests a block of persistent storage for the PostgreSQL database.

```yaml
# k8s/db_pvc.yml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  storageClassName: gp2 # for aws eks dynamic store ebs
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

* **`storageClassName: gp2`**: This specifies the `StorageClass` to use. In AWS EKS, `gp2` (or `gp3`) is a common `StorageClass` that dynamically provisions AWS EBS (Elastic Block Store) volumes. This ensures that the database data is stored durably and independently of the lifecycle of the PostgreSQL Pod.
* **`accessModes: ReadWriteOnce`**: This means the volume can be mounted as read-write by a single node.
* **`resources.requests.storage: 5Gi`**: Requests a 5 Gigabyte storage volume.

#### PostgreSQL ClusterIP Service

The `cluster-db-app.yml` manifest defines a Kubernetes `Service` of type `ClusterIP` for the PostgreSQL database.

```yaml
# k8s/cluster-db-app.yml
apiVersion: v1
kind: Service
metadata:
  name: postgres-cluster-services
spec:
  type: ClusterIP
  ports:
    - port: 5432
      targetPort: 5432
  selector:
    component: postgres
```
* **`type: ClusterIP`**: This creates an internal-only service, meaning it's only reachable from within the Kubernetes cluster.
* **`port: 5432`**: The port exposed by the service.
* **`targetPort: 5432`**: The port on the pods that the service directs traffic to (PostgreSQL's default port).
* **`selector: component: postgres`**: This links the service to any pods that have the label `component: postgres`, ensuring that the Flask application can reach the database consistently via the service name `postgres-cluster-services`.

#### PostgreSQL Deployment

The `db_app.yml` manifest defines a Kubernetes `Deployment` for the PostgreSQL database.

```yaml
# k8s/db_app.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-deployment
  labels:
    component: postgres
spec:
  replicas: 1 # Only one DB instance in this setup
  selector:
    matchLabels:
      component: postgres
  template:
    metadata:
      labels:
        component: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:14-alpine
          ports:
            - containerPort: 5432 # PostgreSQL default port
          env: # Using Kubernetes secrets for secure credentials
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: secrets-flask-app
                  key: DB_PASSWORD
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: secrets-flask-app
                  key: DB_USER
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: secrets-flask-app
                  key: DB_NAME
          volumeMounts: # Persist database storage
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
              subPath: postgres
      volumes: # List of availables volume for this development
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-pvc # PVC for DB persistence
      nodeSelector:
        role: db # Ensures DB runs on specific nodes
```
* **`replicas: 1`**: Configures a single instance of the PostgreSQL database, suitable for development or non-HA setups.
* **`image: postgres:14-alpine`**: Specifies the PostgreSQL Docker image to use.
* **`env`**: Database credentials (`POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`) are securely injected from a Kubernetes `Secret` named `secrets-flask-app` using `secretKeyRef`.
* **`volumeMounts`** and **`volumes`**: Connects the `postgres-pvc` (defined above) to the container, ensuring that the database data persists even if the pod restarts or moves to another node.
* **`nodeSelector: role: db`**: This critical part schedules the PostgreSQL pod exclusively onto nodes labeled with `role: db`, ensuring it runs on the dedicated database node group.

#### Database Migration Job

The `migration_job.yml` manifest defines a Kubernetes `Job` responsible for running Flask database migrations.

```yaml
# k8s/migration_job.yml
apiVersion: batch/v1
kind: Job
metadata:
  name: flask-db-migration
spec:
  backoffLimit: 3
  template:
    spec:
      containers:
        - name: migration-container
          image: joseriosve/flask_app_distributed
          command: ["sh", "-c", "
            echo 'Running database migrations...';
            flask db upgrade"]
          envFrom: # Load ALL secrets for environment variables
            - secretRef:
                name: secrets-flask-app
      restartPolicy: OnFailure # Ensures the job runs only once
```
* **`kind: Job`**: Designed for tasks that run to completion. This job will execute the Flask-Migrate `flask db upgrade` command.
* **`image: joseriosve/flask_app_distributed`**: Uses the same application Docker image, as it contains Flask-Migrate and access to the application's database models.
* **`command`**: Executes a shell command to perform the database upgrade.
* **`envFrom`**: All environment variables from the `secrets-flask-app` Secret are loaded into the job container, ensuring it has the necessary database connection details.
* **`restartPolicy: OnFailure`**: Ensures that if the migration job fails, it will be retried (up to `backoffLimit`). Once successful, the job completes and does not restart. This job should be run *after* the PostgreSQL database is up and running and *before* the Flask application deployment.

#### Flask Application ClusterIP Service

The `cluster_flask_app.yml` manifest defines a Kubernetes `Service` of type `ClusterIP` for the Flask application.

```yaml
# k8s/cluster_flask_app.yml
apiVersion: v1
kind: Service
metadata:
  name: flask-app-cluster-ip-service
spec:
  type: ClusterIP
  selector:
    component: flask-app
  ports:
    - port: 80 # Expose port
      targetPort: 8000
```
* **`type: ClusterIP`**: Creates an internal service, making the Flask application accessible from other pods within the cluster (e.g., from an Ingress controller or other microservices).
* **`port: 80`**: The service exposes port 80.
* **`targetPort: 8000`**: Maps incoming traffic from port 80 to port 8000 on the application pods, which is where Gunicorn listens.
* **`selector: component: flask-app`**: Links this service to all pods labeled with `component: flask-app`.

#### Flask Application Deployment

The `flask_app.yml` manifest defines the Kubernetes `Deployment` for the Flask application.

```yaml
# k8s/flask_app.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-app-deployment
  labels:
    component: flask-app
spec:
  replicas: 2 # Running multiple instances for load balancing
  selector:
    matchLabels:
      component: flask-app
  template:
    metadata:
      labels:
        component: flask-app
    spec:
      nodeSelector:
        role: app # Schedule on nodes marked for app services
      containers:
        - name: flask-app
          image: joseriosve/flask_app_distributed
          ports:
            - containerPort: 8000 # Flask application runs on port 8000
          envFrom: # Load environment variables from secrets
            - secretRef:
                name: secrets-flask-app
          command: # Gunicorn command to start Flask
            - "gunicorn"
            - "--workers"
            - "3"
            - "--bind"
            - "0.0.0.0:8000"
            - "app:create_app()"
```
* **`replicas: 2`**: Deploys two instances (pods) of the Flask application, distributing the load and providing basic high availability. These pods are intentionally placed in different AZs (AZ B and C) from the database to improve resilience.
* **`image: joseriosve/flask_app_distributed`**: Specifies the Docker image for the Flask application.
* **`ports`**: Exposes port 8000, which is where the Gunicorn server inside the container listens.
* **`envFrom`**: Loads all environment variables from the `secrets-flask-app` Secret, providing the application with necessary configurations like database connection strings and JWT secrets.
* **`command`**: Overrides the Dockerfile's `ENTRYPOINT` to explicitly run `gunicorn` with 3 workers, binding to all interfaces on port 8000, and loading the Flask application via `app:create_app()`. The number of Gunicorn workers can be adjusted based on the EC2 instance type's CPU cores.
* **`nodeSelector: role: app`**: This ensures that the Flask application pods are scheduled only on nodes within the dedicated application node group, which are in private subnets across AZ B and C.

### 2. PostgreSQL High Availability with Zalando Operator

For production-grade high availability and automated management of PostgreSQL, this project leverages the **Zalando PostgreSQL Operator**. This operator extends Kubernetes to manage PostgreSQL clusters, including features like replication, failover, and scaling, greatly simplifying the operational overhead.

#### Installation of Zalando PostgreSQL Operator

The Zalando PostgreSQL Operator is installed using Helm, the Kubernetes package manager.

1.  **Add the Helm Repository:** First, add the Zalando PostgreSQL Operator Helm repository to your Helm configuration:

    ```bash
    helm repo add postgres-operator-charts [https://opensource.zalando.com/postgres-operator/charts/postgres-operator](https://opensource.zalando.com/postgres-operator/charts/postgres-operator)
    ```

2.  **Install the Operator:** Once the repository is added, install the operator into your Kubernetes cluster. By default, it will be installed in the `default` namespace unless specified otherwise.

    ```bash
    helm install postgres-operator postgres-operator-charts/postgres-operator
    ```

3.  **Verify Operator Status:** After installation, confirm that the operator's pod is running successfully in your cluster:

    ```bash
    kubectl get pod -l app.kubernetes.io/name=postgres-operator
    ```
    A running pod indicates the operator is ready to manage PostgreSQL clusters.

#### Deploying the Highly Available PostgreSQL Cluster

Once the operator is active, you define your desired PostgreSQL cluster configuration using a custom resource definition (CRD) provided by the operator. The `operator.yml` manifest specifies the details of the `flask-db` PostgreSQL cluster.

```yaml
# k8s/postgres-ha-patroni/zalando-operator/operator.yml
apiVersion: acid.zalan.do/v1
kind: postgresql
metadata:
  name: flask-db
  namespace: default
spec:
  teamId: "myteamDemo"
  # 1 primary + 2 replicas
  numberOfInstances: 3
  postgresql:
    version: "14"
  # Persistent volume claim for each pod
  volume:
    size: 5Gi
    storageClass: gp2
  # Users and roles
  users:
    flask_user:
      - superuser
      - createdb
  # Databases: <db-name>: <owner>
  databases:
    flask_db_1: flask_user
  # Tell the operator how to initially create your db (can you install here the extension like postgis)
  preparedDatabases:
    flask_db_1: {}
```
**Manifest Breakdown:**

* **`apiVersion: acid.zalan.do/v1`**, **`kind: postgresql`**: This indicates that we are defining a custom PostgreSQL cluster resource managed by the Zalando operator.
* **`metadata.name: flask-db`**: This is the name of your PostgreSQL cluster. The operator will create a Kubernetes Service with this name, allowing your application to connect.
* **`numberOfInstances: 3`**: This crucial setting configures a high-availability cluster with one primary PostgreSQL instance and two replica instances. The operator automatically sets up replication (using Patroni) and handles failover.
* **`postgresql.version: "14"`**: Specifies the desired PostgreSQL version for your cluster.
* **`volume.size: 5Gi`**: Each PostgreSQL pod (primary and replicas) will request a Persistent Volume of 5 Gigabytes.
* **`volume.storageClass: gp2`**: Similar to the simple deployment, this uses the `gp2` storage class, which dynamically provisions AWS EBS volumes for each pod's persistent storage, ensuring data durability across node failures.
* **`users.flask_user`**: Defines a new database user named `flask_user` and grants them `superuser` and `createdb` privileges. The operator will automatically create this user and its credentials as a Kubernetes Secret.
* **`databases.flask_db_1: flask_user`**: Creates a database named `flask_db_1` and sets its owner to the `flask_user` defined above.
* **`preparedDatabases.flask_db_1: {}`**: This section can be used to run initial SQL statements or enable extensions (e.g., `CREATE EXTENSION postgis;`) when the database is first created. In this case, it's left empty, meaning only the database `flask_db_1` will be created for the `flask_user`.

#### Verifying Cluster Deployment

After applying the `operator.yml` manifest, the Zalando operator will provision the PostgreSQL pods. You can monitor their status with:

```bash
kubectl get pods -l application=spilo -L spilo-role
```
This command lists all pods managed by the Patroni (Spilo) PostgreSQL cluster, showing their role (master/replica).

#### Connecting the Flask Application to the Zalando PostgreSQL Cluster

To connect the Flask application to this highly available PostgreSQL cluster, I have to update the connection string in the `.env` file used by the flask application. (I connect through secrets). 

1.  **Create the Secrets:** Ensure your Kubernetes secret `secrets-flask-app` exists, populated from your local `.env` file. If you haven't already, or if you've updated your `.env` file, run:

    ```bash
    kubectl create secret generic secrets-flask-app --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
    ```

2.  **Update `.env` `DB_HOST`:** Edit your local `.env` file. The `DB_HOST` environment variable for the Flask application must now point to the Kubernetes Service created by the Zalando operator for your cluster. The format is `<cluster-name>.<namespace>.svc.cluster.local`.

    ```
    DB_HOST=flask-db.default.svc.cluster.local
    DB_USER=flask_user  # or postgres
    DB_PASSWORD=<password_from_below>
    DB_NAME=flask_db_1
    ```

3.  **Retrieve Passwords:** The Zalando operator automatically generates strong passwords for the created users and stores them in Kubernetes Secrets.
    * **For the `postgres` superuser:**

        ```bash
        kubectl get secret postgres.flask-db.credentials.postgresql.acid.zalan.do \
          -n default \
          -o jsonpath='{.data.password}' | base64 --decode; echo
        ```

    * **For the `flask_user`:**

        ```bash
        kubectl get secret flask-user.flask-db.credentials.postgresql.acid.zalan.do --namespace default -o 'jsonpath={.data.password}' | base64 -d
        ```
    Copy the retrieved password and update your local `.env` file.


#### Benefits of Using Zalando PostgreSQL Operator

* **High Availability (HA):** Automates the setup of a highly available PostgreSQL cluster with primary and replica instances, ensuring continuous database operation even during node failures.
* **Automated Failover:** Utilizes Patroni to handle automatic primary elections and failover, minimizing downtime.
* **Simplified Management:** Reduces the manual effort required for deploying, scaling, and maintaining PostgreSQL, treating it as a native Kubernetes resource.
* **Dynamic Scaling:** Easily scale your cluster by changing the `numberOfInstances` in the manifest.
* **Secure Credential Management:** Automatically generates and manages database user credentials as Kubernetes Secrets.
* **Backup/Restore Capabilities:** (Not explicitly shown in this basic manifest, but supported) The operator integrates with popular backup solutions for robust data protection.

#### Further Improvements to the Zalando Operator Manifest

While the provided manifest sets up a functional HA cluster, it can be enhanced for production environments:

* **Resource Limits and Requests:** Add `resources` (CPU and memory requests/limits) to the `postgresql` specification to ensure pods get adequate resources and don't consume too much.
* **Connection Pooling:** Integrate a connection pooler like PgBouncer (often deployed as a sidecar or a separate service) to efficiently manage database connections from the application.
* **Monitoring:** Configure Prometheus metrics exposure via the operator for detailed monitoring of PostgreSQL performance and health.
* **Backup Configuration:** Add a `backup` section to specify scheduled backups to an S3 bucket or other storage.
* **PostgreSQL Extensions:** Use the `preparedDatabases` section to enable necessary PostgreSQL extensions, such as PostGIS:

    ```yaml
    preparedDatabases:
      flask_db_1:
        extensions:
          - name: postgis
            version: "3.3" # or the desired version
    ```
* **Custom Parameters:** Fine-tune PostgreSQL parameters (e.g., `shared_buffers`, `work_mem`) by adding a `parameters` section under `postgresql`.
* **Affinity/Anti-Affinity:** Refine pod scheduling using `affinity` rules to ensure primary and replica pods are distributed across different nodes, racks, or availability zones for better resilience.
* **Logging:** Configure logging destinations and levels for better observability.


### 3. PostgreSQL High Availability with CloudNativePG Operator

The **CloudNativePG Operator** is another robust solution for managing PostgreSQL clusters directly within Kubernetes. It's widely adopted for its simplicity, strong resilience, and native Kubernetes approach, providing a comprehensive solution for high-availability, backup, and recovery.

#### Installation of CloudNativePG Operator

The CloudNativePG Operator is installed by applying its manifest directly to your Kubernetes cluster.

1.  **Apply the Operator Manifest:** Use `kubectl apply` with server-side apply to install the operator:

    ```bash
    kubectl apply --server-side -f \
      [https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml](https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml)
    ```

2.  **Verify Operator Status:** After applying the manifest, confirm that the operator's controller manager deployment is running successfully. It usually runs in the `cnpg-system` namespace.

    ```bash
    kubectl rollout status deployment \
      -n cnpg-system cnpg-controller-manager
    ```
    Wait until the rollout reports "successfully rolled out" to ensure the operator is fully operational.

#### Deploying the CloudNativePG Cluster

Once the CloudNativePG operator is active, you can define your PostgreSQL cluster using a `Cluster` custom resource. The `postgres-operator.yml` manifest below configures a highly available PostgreSQL cluster with integrated backup capabilities.

```yaml
# k8s/cloudnative-operator/postgres-operator.yml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-db-cluster
spec:
  instances: 3
  imageName: ghcr.io/cloudnative-pg/postgresql:14.12
  storage:
    size: 5Gi
    storageClass: "gp2"

  bootstrap:
    initdb:
      database: flask_db_1

  backup:
    barmanObjectStore:
      destinationPath: s3://ms-petsland-1/backups/
      s3Credentials:
        accessKeyId:
          name: s3-credentials
          key: AWS_ACCESS_KEY_ID
        secretAccessKey:
          name: s3-credentials
          key: AWS_SECRET_ACCESS_KEY
      wal:
        compression: gzip

  # The following commented sections illustrate additional functionalities
  # that can be configured with CloudNativePG, such as recovery from backups,
  # database import/migration, external cluster definitions, custom PostgreSQL
  # parameters, and monitoring integration.

  # bootstrap:
  #   recovery: # If you have a barman object in s3 or another cloud provider
  #     source: s3-restore-source # A name for the source config below
  #     database: flask_db_1
  #   initdb:
  #     database: flask_db_1
  #     import: # Migrate the data from previous db
  #       type: microservice # Required, tell that is one db
  #       databases:
  #         - flask_db_1
  #       source:
  #         externalCluster: my-windows

  # externalClusters:
  #   - name: my-windows
  #     connectionParameters:
  #       host: 172.31.240.1 # Use the correct IP or host name for the source database
  #       user: postgres
  #       port: 5433
  #       dbname: postgres
  #     password:
  #       name: s3-credentials
  #       key: DB_PASSWORD
  #   - name: s3-restore-source # Must match the source name above
  #     barmanObjectStore:
  #       destinationPath: "s3://ms-petsland-1/backups/" # Path to your backups folder in your bucket
  #       s3Credentials:
  #         accessKeyId:
  #           name: s3-credentials
  #           key: AWS_ACCESS_KEY_ID
  #         secretAccessKey:
  #           name: s3-credentials
  #           key: AWS_SECRET_ACCESS_KEY

  # postgresql:
  #   parameters: # We can change anything from here
  #     max_connections: '200'
  #     shared_buffers: '256MB'

  # monitoring:
  #   enablePodMonitor: true
```
**Manifest Breakdown (Active Configuration):**

* **`apiVersion: postgresql.cnpg.io/v1`**, **`kind: Cluster`**: This defines a custom PostgreSQL cluster resource managed by the CloudNativePG operator.
* **`metadata.name: postgres-db-cluster`**: This is the logical name for your PostgreSQL cluster. The operator will create associated Kubernetes Services (e.g., `postgres-db-cluster-rw` for read-write, `postgres-db-cluster-ro` for read-only) that your application will use to connect.
* **`instances: 3`**: Configures a highly available PostgreSQL cluster with three instances. CloudNativePG will automatically set up streaming replication and manage failover using native PostgreSQL capabilities.
* **`imageName: ghcr.io/cloudnative-pg/postgresql:14.12`**: Specifies the exact Docker image to use for your PostgreSQL pods. It's recommended to use images provided by CloudNativePG for full compatibility.
* **`storage.size: 5Gi`**: Each PostgreSQL instance (pod) will request a Persistent Volume of 5 Gigabytes.
* **`storage.storageClass: "gp2"`**: Specifies the `StorageClass` for dynamic provisioning of persistent volumes. On AWS EKS, `gp2` (or `gp3`) provisions EBS volumes, ensuring data persistence and durability for each database instance.
* **`bootstrap.initdb.database: flask_db_1`**: This section instructs the operator to create a database named `flask_db_1` during the initial setup of the cluster. CloudNativePG automatically creates a default owner user for this database (with the same name, `flask_db_1`, unless explicitly overridden, which is good for simplicity and integration).
* **`backup.barmanObjectStore`**: This block configures integrated backups to an S3-compatible object store using Barman, a popular PostgreSQL backup tool.
    * **`destinationPath: s3://ms-petsland-1/backups/`**: Specifies the S3 bucket and prefix where backups will be stored.
    * **`s3Credentials`**: References a Kubernetes Secret named `s3-credentials` which should contain your AWS access key ID (`AWS_ACCESS_KEY_ID`) and secret access key (`AWS_SECRET_ACCESS_KEY`). This ensures secure access to your S3 bucket.
    * **`wal.compression: gzip`**: Configures Write-Ahead Log (WAL) archiving to use gzip compression, saving storage space for backups.

**Manifest Breakdown (Commented-out Functionalities - for advanced use cases):**

The commented sections in the manifest highlight powerful features of CloudNativePG for advanced scenarios:

* **`bootstrap.recovery`**: Allows restoring a PostgreSQL cluster from an existing Barman backup stored in an object store (like S3) during initial cluster creation. This is vital for disaster recovery.
* **`bootstrap.initdb.import`**: Facilitates migration of data from an existing external PostgreSQL database (e.g., from a virtual machine or another Kubernetes cluster) during the initial cluster setup. This can be used for "lift-and-shift" migrations.
* **`externalClusters`**: Used in conjunction with `bootstrap.initdb.import` or `bootstrap.recovery` to define connection parameters to external PostgreSQL sources or backup sources.
* **`postgresql.parameters`**: Enables fine-grained control over PostgreSQL configuration parameters (e.g., `max_connections`, `shared_buffers`). This allows optimizing database performance based on your workload.
* **`monitoring.enablePodMonitor: true`**: Integrates with Prometheus for comprehensive monitoring of your PostgreSQL cluster by automatically creating a `PodMonitor` resource.

#### Connecting the Flask Application to CloudNativePG

To connect your Flask application to the CloudNativePG cluster, you will primarily interact with the Kubernetes Services created by the operator. CloudNativePG, by default, sets up several services for your cluster:

* `<cluster-name>-rw` (e.g., `postgres-db-cluster-rw`): Points to the primary instance for read-write operations.
* `<cluster-name>-ro` (e.g., `postgres-db-cluster-ro`): Points to read-only replicas for load balancing read operations.
* `<cluster-name>-r` (e.g., `postgres-db-cluster-r`): Points to all instances (primary and replicas) for read-only workloads, offering a more flexible read pool.

For a typical application, you'll connect to the read-write service.

1.  **Retrieve Connection Details from Secret:** CloudNativePG automatically generates a Kubernetes Secret containing the credentials for the application database user. By default, if you specify `initdb.database: flask_db_1` without an explicit `owner`, CloudNativePG will create a user with the same name as the database (`flask_db_1`) and generate a secret for it. The secret name will typically be `<cluster-name>-app` or, in cases where the database name is used as the user, potentially `<cluster-name>-<db-name>`. For the given manifest, the primary application secret is likely named `postgres-db-cluster-app`.

    To retrieve the password for the default application user (e.g., `flask_db_1` if no other owner is specified, or `app` by convention if no database is specified), use the following command to decode the password from the secret created by CloudNativePG:

    ```bash
    kubectl get secret postgres-db-cluster-app \
      -o jsonpath='{.data.password}' | base64 --decode && echo
    ```
    This command specifically fetches the `password` key from the `postgres-db-cluster-app` secret and decodes it. You can change `.data.password` to other keys like `.data.username`, `.data.uri`, etc., to get other connection details.

2.  **Update `.env` File:** Edit your local `.env` file to include the correct connection details for your Flask application.

    ```
    DB_HOST=postgres-db-cluster-rw.default.svc.cluster.local # Connect to the read-write service
    DB_USER=flask_db_1                                        # Or the specific user if defined in manifest
    DB_PASSWORD=<password_retrieved_above>
    DB_NAME=flask_db_1
    ```
    * **`DB_HOST`**: Use the fully qualified domain name (FQDN) of the read-write Kubernetes Service. The format is `<service-name>.<namespace>.svc.cluster.local`.
    * **`DB_USER`**: If you didn't specify a `users` section in the CloudNativePG manifest and only used `initdb.database`, the default application user will have the same name as the database (e.g., `flask_db_1`).
    * **`DB_PASSWORD`**: Use the password retrieved from the Kubernetes secret.

3.  **Apply Changes to Kubernetes Secret:** After updating your local `.env` file, recreate or update your `secrets-flask-app` Kubernetes Secret

#### Benefits of Using CloudNativePG Operator

CloudNativePG stands out as a preferred choice for PostgreSQL on Kubernetes due to several key advantages:

* **Kubernetes-Native Design:** It leverages Kubernetes APIs directly for high availability, scaling, and lifecycle management, avoiding external tools for failover (unlike Patroni-based solutions where Patroni itself is external to K8s' core HA mechanism). This makes it feel very much like a native Kubernetes component.
* **High Availability & Self-Healing:** Automatically manages primary-replica setups with streaming replication and seamless failover, promoting the most aligned replica to primary in case of failure. It also automatically recreates failed replicas.
* **Integrated Backup and Recovery:** Includes built-in support for continuous backups to object stores (like S3) using Barman, enabling robust Point-In-Time-Recovery (PITR) and disaster recovery strategies.
* **Simplified Operations:** Automates many DBA tasks, from initial deployment and user management to minor version upgrades and configuration tuning.
* **Declarative Configuration:** Everything is defined in Kubernetes manifests, promoting GitOps practices and ensuring consistency.
* **Connection Pooling (Optional):** Supports integration with PgBouncer through its own `Pooler` custom resource, providing a scalable and efficient connection management layer.
* **Observability:** Offers native Prometheus exporter for detailed monitoring and structured JSON logging for easy integration with log aggregation systems.
* **Data Migration Capabilities:** Provides declarative options for importing existing databases (offline or online) into a new CloudNativePG cluster, simplifying migrations.

#### Further Improvements to the CloudNativePG Manifest

While the provided manifest is a solid starting point for a highly available database, here are ways to enhance it for production-readiness and advanced scenarios:

* **Resource Management:** Explicitly define `resources.requests` and `resources.limits` for CPU and memory within the `spec` to ensure stable performance and prevent resource starvation or overconsumption by the database pods. This is crucial for "Guaranteed" QoS.
    ```yaml
    spec:
      # ... other configurations
      resources:
        requests:
          memory: "1Gi"
          cpu: "500m" # 0.5 CPU cores
        limits:
          memory: "2Gi"
          cpu: "1000m" # 1 CPU core
    ```
* **Scheduled Backups:** While `barmanObjectStore` is configured, consider adding a `ScheduledBackup` resource to define a cron-like schedule for full base backups, complementing the continuous WAL archiving.
* **PostgreSQL Parameters:** Utilize the `postgresql.parameters` section to fine-tune PostgreSQL settings (e.g., `max_connections`, `shared_buffers`, `work_mem`, `wal_buffers`) based on your workload and cluster size for optimal performance.
* **Monitoring Integration:** Uncomment and configure the `monitoring` section (`enablePodMonitor: true`) to expose Prometheus metrics, allowing you to build comprehensive Grafana dashboards for your database.
* **Custom Users and Roles:** For more granular access control, explicitly define additional users and roles in the manifest with specific privileges, rather than relying solely on the default database owner.
* **Node Affinity/Anti-Affinity and Tolerations:** Implement advanced scheduling rules using `affinity` and `tolerations` to ensure database pods are distributed across different nodes or availability zones, or to dedicate specific nodes for database workloads. CloudNativePG applies anti-affinity by default to distribute instances.
* **Connection Pooling with PgBouncer:** Deploy a `Pooler` custom resource alongside your cluster to introduce PgBouncer for efficient connection management, reducing the load on your PostgreSQL server from numerous short-lived application connections.
* **TLS/SSL Configuration:** Leverage CloudNativePG's native TLS support. While it generates certificates by default, you can integrate with `cert-manager` or bring your own certificates for enhanced security.
* **PostGIS and other Extensions:** If your application requires specific PostgreSQL extensions (like PostGIS for geospatial data), you can enable them automatically during `initdb` or via `pg_dump` with an import strategy. For example:
    ```yaml
    bootstrap:
      initdb:
        database: flask_db_1
        # Example for PostGIS extension (requires image with PostGIS)
        # However, it's often better to enable extensions via SQL after initdb
        # or in a post-init script for full control.
        # This example shows how to potentially add init-time SQL:
        # initSQL:
        #   - CREATE EXTENSION IF NOT EXISTS postgis;
    ```
* **WAL Disk Space Safeguard:** CloudNativePG includes features to prevent WAL disk space exhaustion, ensuring the cluster safely stops rather than entering an unrecoverable state, which is a good practice to be aware of.
