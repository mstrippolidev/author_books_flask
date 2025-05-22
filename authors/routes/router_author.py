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
from authors.models import Author, Book, AuthorBook
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
        "data": [val.to_dict() for val in pagination.items],
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
        try:
            author = Author(name = name, biography = biography, birthdate = birthdate)
            db.session.add(author)
            db.session.commit()
            return jsonify(author.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify(f"Error {str(e)}"), 422
    else:
        try:
            page = request.args.get("page", default=1, type=int)
            size = request.args.get("size", default=15, type=int)
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
        Edit, delete or details of an author
    """
    author = Author.query.filter_by(id = author_id).first()
    if author is None:
        return jsonify(f"Author {author_id} does not exists!!"), 404
    if request.method == 'GET':
        return details_model(author, related = True)
    if request.method == 'PUT':
        # Edit the fields in author
        data = request.get_json() or {}
        return edit_model_details(author, data, ['author_books', 'books'])
    if request.method == 'DELETE':
        return delete_model(author)

def edit_model_details(model, data, remove_fields = []):
    """
        Funcion to edit a author
    """
    omit_fields =['id', 'created_at', 'updated_at'] + remove_fields
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
    

def extract_data(model, data:dict, remove_fields = []) -> dict:
    """
        Create a dict model with the data from the request
    """
    resp = {}
    omit = ['id'] + remove_fields
    for field in data:
        if field in omit:
            continue
        if hasattr(model, field):
            resp[field] = data[field]
    return resp

@author_blueprint.route('book', methods = ['GET', 'POST'])
@jwt_required()
@admin_required_post
def handle_books():
    """
        View to create books and shows a list of books
    """
    if request.method == 'POST':
        data = request.get_json() or {}
        data = extract_data(Book, data, ['created_at', 'updated_at'])
        try:
            book = Book(**data)
            db.session.add(book)
            db.session.commit()
            return jsonify(book.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify(f"Error {str(e)}"), 422

    try:
        page = request.args.get("page", default=1, type=int)
        size = request.args.get("size", default=15, type=int)
        search = request.args.get("search")
        search_fields = []
        if search is not None:
            search = f"%{search}%"
            search_fields = [Book.title.ilike(search), Book.description.ilike(search)]
        return paginated_model(Book, page, size, search, search_fields)
    except Exception as e:
        return jsonify(f"Error {str(e)}"), 422
    
@author_blueprint.route('book/<int:book_id>', methods = ['GET','PUT', 'DELETE'])
@jwt_required()
@admin_required_post
def handle_books_elment(book_id:int):
    """
        Edit, delete or details of a book
    """
    book = Book.query.filter_by(id = book_id).first()
    if book is None:
        return jsonify(f"book {book_id} does not exists!!"), 404
    if request.method == 'PUT':
        # Edit the fields in book
        data = request.get_json() or {}
        return edit_model_details(book, data, ['authors', 'author_books'])
    if request.method == 'DELETE':
        return delete_model(book)
    # Get request
    return details_model(book, related = True)

@author_blueprint.route('book/<string:slug>', methods = ['GET','PUT', 'DELETE'])
@jwt_required()
@admin_required_post
def handle_books_elment_slug(slug:str):
    """
        Edit, delete or details of a book
    """
    book = Book.query.filter_by(slug_book=slug).first()
    if book is None:
        return jsonify(f"book {slug} does not exists!!"), 404
    if request.method == 'PUT':
        # Edit the fields in book
        data = request.get_json() or {}
        return edit_model_details(book, data, ['authors', 'author_books'])
    if request.method == 'DELETE':
        return delete_model(book)
    # Get request
    return details_model(book, related = True)


@author_blueprint.route('/', methods = ['POST'])
@jwt_required()
@admin_required_post
def create_relation_author_book():
    """
        Api endpoint to create a relation between an author an a book.
    """
    data = request.get_json() or {}
    print(data)
    author_id = data.get('author_id')
    book_id = data.get('book_id')
    try:
        author_book = AuthorBook(author_id = author_id, book_id = book_id) 
        db.session.add(author_book)
        db.session.commit()
        return jsonify(author_book.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(f"Error {str(e)}"), 422

@author_blueprint.route('/<int:author_book_id>', methods = ['PUT', 'DELETE'])
@jwt_required()
@admin_required_post
def edit_delete_relation_author_book(author_book_id):
    """
        Api endpoint to edit a relation between an author an a book.
    """
    author_book = AuthorBook.query.get(author_book_id)
    if author_book is None:
        return jsonify(f"author_book {author_book_id} does not exists!!"), 404
    if request.method == 'PUT':
        # Edit the fields in author_book
        data = request.get_json() or {}
        return edit_model_details(author_book, data)
    if request.method == 'DELETE':
        return delete_model(author_book)