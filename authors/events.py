"""
    Register event for the blueprint authors books
"""
from sqlalchemy import event
from extension import db
from authors.models import AuthorBook, Author, Book

def verify_foreign_keys(mapper, connection, target):
    # Use the actual connection (not the session) to check if there is a author
    author_exists = connection.execute(
        # Select only one column
        db.select(db.exists().where(Author.id == target.author_id)) # check if author exists
    ).scalar()
    
    if not author_exists:
        raise ValueError(f"Author with id {target.author_id} does not exist")
    # Return the first value of the select statement for exists(book == target.id)
    book_exists = connection.execute(
        db.select(db.exists().where(Book.id == target.book_id))
    ).scalar() 
    
    if not book_exists:
        raise ValueError(f"Book with id {target.book_id} does not exist")


event.listen(AuthorBook, 'before_insert', verify_foreign_keys)
event.listen(AuthorBook, 'before_update', verify_foreign_keys)
