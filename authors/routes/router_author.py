"""
    Router for handle crud of books and authors.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
    current_user
)
from extension import db
from authors.models import Author
author_blueprint = Blueprint('authors', __name__, url_prefix='author-books')

@author_blueprint.routes('author', methods = ['GET', 'POST'])
@jwt_required
def handle_authors(self):
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
        return jsonify("something")