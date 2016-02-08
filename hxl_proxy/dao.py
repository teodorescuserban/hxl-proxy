from hxl_proxy import app
from flask import g
import sqlite3, json

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db_file = app.config.get('DB_FILE', '/tmp/hxl-proxy.db')
        db = g._database = sqlite3.connect(db_file)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def _execute(statement, params=()):
    """Execute a single statement."""
    cursor = get_db().cursor()
    cursor.execute(statement, params)
    return cursor

def _executemany(statement, param_list=[]):
    """Execute a statement repeatedly over a list."""
    cursor = get_db().cursor()
    cursor.executemany(statement, param_list)
    return cursor

class Users:

    @staticmethod
    def create(user):
        """Add a new user."""
        cursor = get_db().cursor()
        cursor.execute(
            'insert into users '
            '(user_id, email, name, name_given, name_family, last_login) '
            "values (?, ?, ?, ?, ?, datetime('now'))",
            (user.get('user_id'), user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'))
        )
        get_db().commit()

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
        cursor = get_db().cursor()
        cursor.execute(
            'update users '
            "set email=?, name=?, name_given=?, name_family=?, last_login=datetime('now') "
            'where user_id=?',
            (user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'), user.get('user_id'))
        )
        get_db().commit()

class Recipes:

    @staticmethod
    def read(recipe_id):
        recipe = _execute(
            'select * from Recipes where recipe_id=?',
            (recipe_id,)
        ).fetchone()
        recipe = dict(recipe)
        recipe['args'] = json.loads(recipe['args'])
        return recipe

    @staticmethod
    def list(user_id=None):
        return _execute(
            'select * from Recipes where user_id=?',
            (user_id,)
        ).fetchall()
