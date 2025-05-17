"""
    Create decorators to add functionality to each view function.
"""
from flask import jsonify
from functools import wraps
from flask_jwt_extended import (current_user)
from admin.models import UserRoleEnum
def admin_required(f):
    @wraps(f)
    def decorator(f, *args, **kwargs):
        """
            Function to handle authenticated user role admin and superadmin
        """
        user = current_user
        if user.role == UserRoleEnum.admin or user.role == UserRoleEnum.superadmin:
            return f(*args, **kwargs)
        return jsonify("Permission Denied! admin only"), 403