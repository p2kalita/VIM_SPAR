# Imports the SQLAlchemy class from the flask_sqlalchemy library. This class is the main entry point for using the extension.
from flask_sqlalchemy import SQLAlchemy
# Creates an instance of the SQLAlchemy class. This object, conventionally named 'db',
# represents the vim_database and provides access to all the functions and classes from SQLAlchemy,
# like the Model class for defining vim_database tables.
db=SQLAlchemy()