"""Database access functions and classes."""

import sqlite3, json, os
from flask import g, request
from werkzeug.exceptions import Forbidden

from hxl_proxy import app, util, recipes


SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')
"""The filename of the SQL schema."""


DB_FILE = app.config.get('DB_FILE', '/tmp/hxl-proxy.db')
"""The filename of the SQLite3 database."""


def _get_db():
    """Get the database."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close the connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def _execute(statement, params=()):
    """Execute a single statement."""
    cursor = _get_db().cursor()
    cursor.execute(statement, params)
    return cursor

def _executemany(statement, param_list=[]):
    """Execute a statement repeatedly over a list."""
    cursor = _get_db().cursor()
    cursor.executemany(statement, param_list)
    return cursor

def _executescript(sql_statements, commit=True):
    """Execute a script of statements, and commit if requested."""
    db = _get_db()
    cursor = db.cursor()
    cursor.executescript(sql_statements)
    if commit:
        db.commit()

def _executefile(filename, commit=True):
    """Open a SQL file and execute it as a script."""
    with open(filename, 'r') as input:
        _executescript(input.read(), commit)

def create_db():
    """Create a new database, erasing the current one."""
    _executefile(SCHEMA_FILE)


class UserDAO:
    """Manage user records in the database."""

    @staticmethod
    def create(user):
        """Add a new user."""
        cursor = _get_db().cursor()
        cursor.execute(
            'insert into users '
            '(user_id, email, name, name_given, name_family, last_login) '
            "values (?, ?, ?, ?, ?, datetime('now'))",
            (user.get('user_id'), user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'))
        )
        _get_db().commit()

    @staticmethod
    def read(user_id):
        """Look up a user by id."""
        return _execute(
            'select * from Users where user_id=?',
            (user_id,)
        ).fetchone()

    @staticmethod
    def update(user):
        """Update an existing user."""
        cursor = _get_db().cursor()
        cursor.execute(
            'update users '
            "set email=?, name=?, name_given=?, name_family=?, last_login=datetime('now') "
            'where user_id=?',
            (user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'), user.get('user_id'))
        )
        _get_db().commit()


class RecipeDAO:
    """Manage recipe records in the database."""

    @staticmethod
    def read(recipe_id):
        """Read a single recipe.
        @param recipe_id: the recipe's identifier.
        @return: a recipe, or None if not found.
        """

        # read the SQL row
        db_in = _execute(
            'select * from Recipes where recipe_id=?',
            (recipe_id,)
        ).fetchone()

        # convert to a Recipe object
        if db_in:
            recipe = recipes.Recipe(db_in=db_in)
            return recipe
        else:
            return None

    @staticmethod
    def list(user_id=None):
        """Get a list of recipes.
        @param user_id: if not None, return only recipes that belong to this user (default: None)
        @return: a (possibly-empty) list of Recipe objects.
        """
        return _execute(
            'select * from Recipes where user_id=?',
            (user_id,)
        ).fetchall()


PROPERTY_OVERRIDES = ['url', 'schema_url']
"""Recipe properties that may be overridden"""


ARG_OVERRIDES = []
"""Recipe args that may be overridden"""


def get_recipe(key=None, auth=False, args=None):
    """Load a recipe or create from args.
    This function allows some overrides from GET parameters.
    @param key: the recipe identifier.
    @param auth: True if we need authorisation.
    @param args: a dict of HTTP parameters.
    @return: the recipe object.
    """

    if args is None:
        args = request.args

    if key:
        recipe = RecipeDAO.read(str(key))
        if not recipe:
            raise NotFound("No saved recipe for " + key)
        elif auth and not util.check_auth(recipe):
            raise Forbidden("Not authorised")
        # Allow some values to be overridden from request parameters
        for name in PROPERTY_OVERRIDES:
            if args.get(name):
                recipe.overridden = True
                setattr(recipe, name, args.get(name))
    else:
        recipe = recipes.Recipe(args_in=args)

    return recipe

