# Flask Books & Authors API

This repository hosts a robust Flask API for managing books and authors, featuring advanced security measures and flexible Kubernetes deployment strategies.

## Table of Contents

-   [Features](#features)
-   [Security Enhancements](#security-enhancements)
    -   [JWT Authentication](#jwt-authentication)
    -   [OAuth2 Integration with Google](#oauth2-integration-with-google)
    -   [Rate Limiting with Flask-Limiter](#rate-limiting-with-flask-limiter)
    -   [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
-   [Kubernetes Deployment](#kubernetes-deployment)
    -   [1. Simple PostgreSQL Deployment with Persistent Volume](#1-simple-postgresql-deployment-with-persistent-volume)
    -   [2. PostgreSQL High Availability with Zalando Operator](#2-postgresql-high-availability-with-zalando-operator)
    -   [3. PostgreSQL High Availability with CloudNativePG Operator](#3-postgresql-high-availability-with-cloudnativepg-operator)
-   [API Endpoints](#api-endpoints)


## Features

* **CRUD Operations:** Full C.R.U.D. (Create, Read, Update, Delete) functionality for managing books and authors.
* **User Authentication:** Secure user authentication using JWT (JSON Web Tokens).
* **Social Login:** Seamless user login via Google OAuth2.
* **Rate Limiting:** Protects against abuse and ensures API stability.
* **Role-Based Authorization:** Restricts access to certain API endpoints based on user roles (Guest, Admin, Superadmin).
* **Database Management:** Utilizes SQLAlchemy for ORM and Flask-Migrate for database migrations.

## Security Enhancements

This application is built with a strong focus on security, incorporating several key techniques to protect data and control access.

### JWT Authentication

The application leverages **Flask-JWT-Extended** for robust token-based authentication.

* **Token Generation:** Upon successful login (either via traditional username/password or Google OAuth), the API issues both `access_token` and `refresh_token`.
* **User Identity Management:** A `user_identity_loader` is implemented to embed the user's `id` into the JWT, allowing for easy retrieval of user information from the database using `user_lookup_loader`.
* **Token Revocation (Blocklist):** The `TokenBlocklist` model and `token_in_blocklist_loader` callback provide a mechanism to revoke JWTs, enhancing security by invalidating tokens upon logout or compromise.

### OAuth2 Integration with Google

For a streamlined user experience, the application integrates **Authlib** for Google OAuth2 login.

* **Simplified Onboarding:** Users can easily sign up and log in using their existing Google accounts, reducing friction.
* **Secure User Information:** User details (email, name) are securely retrieved from Google after successful authentication.
* **Automatic User Provisioning:** If a Google-authenticated user doesn't exist in the database, a new user account is automatically created, associating their Google information. JWTs are then issued for these users, consistent with the application's authentication flow.

### Rate Limiting with Flask-Limiter

To prevent brute-force attacks and ensure fair usage of the API, **Flask-Limiter** is implemented.

* **Per-Host Rate Limiting:** The `Limiter` is configured with `key_func=get_remote_address`, meaning requests are limited based on the client's IP address.
* **Default Limit:** A `default_limits=["30 per minute"]` is applied globally, restricting each unique IP address to 30 requests per minute. This helps maintain API stability and prevents resource exhaustion.

### Role-Based Access Control (RBAC)

The application implements a granular RBAC system using `UserRoleEnum` and a custom decorator.

* **User Roles:** Users can have one of three distinct roles: `guest`, `admin`, or `superadmin`.
* **`admin_required_post` Decorator:** This custom decorator is used to protect specific API endpoints. It checks the `role` of the `current_user` (obtained from the JWT) and allows access only if the user's role is `admin` or `superadmin`. `GET` requests are generally exempted from this restriction, allowing public viewing of data where appropriate. This ensures that sensitive operations are only performed by authorized personnel.

## Kubernetes Deployment

This application can be deployed on Kubernetes using various strategies for managing its PostgreSQL database.

### 1. Simple PostgreSQL Deployment with Persistent Volume

This approach demonstrates a basic Kubernetes deployment of the Flask application with a single PostgreSQL database instance. The database data is persisted using a Kubernetes Persistent Volume. This setup is ideal for development and testing environments where high availability is not a primary concern.

### 2. PostgreSQL High Availability with Zalando Operator

This section will detail the deployment of a highly available PostgreSQL cluster using the **Zalando PostgreSQL Operator**. This operator automates the management, scaling, and recovery of PostgreSQL instances, providing a robust solution for production environments.

### 3. PostgreSQL High Availability with CloudNativePG Operator

This section will cover the deployment of a highly available PostgreSQL cluster using the **CloudNativePG Operator**. Similar to the Zalando operator, CloudNativePG streamlines the deployment and management of PostgreSQL within Kubernetes, focusing on Cloud Native principles and offering features like backup/restore and disaster recovery.
