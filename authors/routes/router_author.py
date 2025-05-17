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
        