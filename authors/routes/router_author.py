"""
    Router for handle crud of books and authors.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
    current_user
)
from extension import db
from authors.models import Author
from permissions import admin_required_post

author_blueprint = Blueprint('authors', __name__, url_prefix='/author-books')

def paginated_model(model, page:int, size:int, search=None, search_fields = []):
    """
        Return list of authors paginated
    """
    query = model.query
    # If there is a parameter fields
    if search is not None and len(search_fields) > 0:
        query = query.filter(
            or_(*search_fields)
        )
    query = query.order_by(model.id)
    pagination = query.paginate(page=page, per_page=size, error_out=False)
    
    # Create the response structure.
    response = {
        "data": [user.to_dict() for user in pagination.items],
        "next_page": pagination.has_next,
        "prev_page": pagination.has_prev,
        "total_elements": pagination.total
    }
    return jsonify(response), 200

@author_blueprint.route('author', methods = ['GET', 'POST'])
@jwt_required()
@admin_required_post
def handle_authors():
    """
        Create and show list of authors.
    """
    if request.method == 'POST':
        data = request.get_json()
        name = data.get("name")
        biography = data.get("biography")
        birthdate = data.get('birthdate')
        if name is None:
            return jsonify("Name is required"), 422
        if birthdate is not None:
            try:
                birthdate = datetime.strptime(birthdate, "%Y-%m-%d")
            except Exception as e:
                return jsonify("Not a valid date format is YYYY-MM-DD"), 422
        author = Author(name = name, biography = biography, birthdate = birthdate)
        db.session.add(author)
        db.session.commit()
        return jsonify(author.to_dict()), 201
    else:
        try:
            page = request.args.get("page", default=1, type=int)
            size = request.args.get("size", default=5, type=int)
            search = request.args.get("search")
            search_fields = []
            if search is not None:
                search = f"%{search}%"
                search_fields = [Author.name.ilike(search), Author.biography.ilike(search)]
            return paginated_model(Author, page, size, search, search_fields)
        except Exception as e:
            return jsonify(f"Error {str(e)}"), 422

@author_blueprint.route('author/<int:author_id>', methods = ['GET','PUT', 'DELETE'])
@jwt_required()
@admin_required_post
def handle_authors_elment(author_id:int):
    """
        Edit an author
    """
    author = Author.query.filter_by(id = author_id).first()
    if author is None:
        return jsonify(f"Author {author_id} does not exists!!"), 404
    if request.method == 'GET':
        return details_model(author, related = True)
    if request.method == 'PUT':
        # Edit the fields in author
        data = request.get_json() or {}
        return edit_model_details(author, data)
    if request.method == 'DELETE':
        return delete_model(author)

def edit_model_details(model, data):
    """
        Funcion to edit a author
    """
    omit_fields =['id', 'created_at', 'updated_at']
    for field in data:
        if field in omit_fields:
            continue
        if hasattr(model, field):
            setattr(model, field, data[field])
    # Save model to the db
    try:
        db.session.commit()
        return jsonify(model.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating", "error": str(e)}), 500
    
def delete_model(model):
    """
        General function to delete an element
    """
    try:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'msg': "Delete sucessfully!!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error Deleting", "error": str(e)}), 500
    
def details_model(model, *args, **kwargs):
    """
        General function to show a model with their related fields
    """
    try:
       return jsonify(model.to_dict(*args, **kwargs)), 200
    except Exception as e:
        return jsonify({"message": "Something bad happens", "error": str(e)}), 500