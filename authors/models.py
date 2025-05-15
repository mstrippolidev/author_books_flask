"""
    File for authors schema
"""
# models/authors.py
from datetime import datetime, timezone
from sqlalchemy.ext.associationproxy import association_proxy
from extension import db

def get_current_time():
    return datetime.now(tz=timezone.utc)

class AuthorBook(db.Model):
    __tablename__ = 'author_book'
    __table_args__ = {'schema': 'authors'}  # This auxiliary model lives in the authors schema
    id = db.Column(db.Integer, unique = True,primary_key = True)
    # Composite primary key from both foreign keys
    author_id = db.Column(db.Integer, db.ForeignKey('authors.author.id', ondelete='CASCADE'))
    book_id = db.Column(db.Integer, db.ForeignKey('authors.book.id', ondelete='CASCADE'))

    # Relationships back to Author and Book
    # This relationship is telling that this atribute (called author)
    # Is related to the model Author, an our actual model AuthorBooks
    # The info of this model will be presence in the foreightMode (Author) in a
    # attribute called author_books (The model Author has a attribute called that way)
    author = db.relationship("Author", back_populates="author_books")
    book = db.relationship("Book", back_populates="author_books")

    def __repr__(self):
        return f'<AuthorBook author_id={self.author_id}, book_id={self.book_id}>'

class Author(db.Model):
    __tablename__ = 'author'
    __table_args__ = {'schema': 'authors'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    biography = db.Column(db.Text)
    birthdate = db.Column(db.DateTime, nullable = True)
    # Relationship to the association object
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)
    # Specify the relationship with the AuthorBook class, this class will be use to populate the author
    # Attribute of the AuthorBook class
    author_books = db.relationship("AuthorBook", back_populates="author", cascade="all, delete-orphan")
    # Use an association proxy for convenience: this will create a virtual attribute called books
    # that will link automaticaly the atribute book from authorBook class an present here as a list
    books = association_proxy("author_books", "book")

    def __repr__(self):
        return f'<Author {self.name}>'

class Book(db.Model):
    __tablename__ = 'book'
    __table_args__ = {'schema': 'authors'}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    # Relationship to the association object
    author_books = db.relationship("AuthorBook", back_populates="book", cascade="all, delete-orphan")
    # Using an association proxy: book.authors will give you a list of Author objects.
    authors = association_proxy("author_books", "author") # From the fK attribute author_books
                                                        # Look  for the author property.

    def __repr__(self):
        return f'<Book {self.title}> has this amount of authors {len(self.authors)}'