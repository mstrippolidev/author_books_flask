"""
    Create decorators to add functionality to each view function.
"""
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
        print('inside middlaware')
        user = current_user
        if request.method != 'POST':
            return f(*args, **kwargs)
        if user.role == UserRoleEnum.admin or user.role == UserRoleEnum.superadmin:
            return f(*args, **kwargs)
        return jsonify("Permission Denied! admin only"), 403
    return decorator

# def admin_required_post():
#     """
#         Admin required decorator
#     """
#     def wrapper(fn):
#         """wraper"""
#         @wraps(fn)
#         def decorator(f, *args, **kwargs):
#             """
#                 Function to handle authenticated user role admin and superadmin
#             """
#             print('dentro del middlaware')
#             user = current_user
#             if request.method != 'POST':
#                 return f(*args, **kwargs)
#             if user.role == UserRoleEnum.admin or user.role == UserRoleEnum.superadmin:
#                 return f(*args, **kwargs)
#             return jsonify("Permission Denied! admin only"), 403
#         return decorator
#     return wrapper
