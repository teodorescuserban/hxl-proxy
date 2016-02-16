from hxl_proxy import app, util, recipes
from flask import g, request
import sqlite3, json, os

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')
DB_FILE = app.config.get('DB_FILE', '/tmp/hxl-proxy.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
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

def _executescript(sql_statements, commit=True):
    """Execute a script of statements, and commit if requested."""
    db = get_db()
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

class RecipeDAO:

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

RECIPE_OVERRIDES = ['url', 'schema_url']

def get_recipe(key=None, auth=False, args=None):
    """Load a recipe or create from args."""

    if args is None:
        args = request.args

    if key:
        recipe = dao.RecipeDAO.read(str(key))
        if not recipe:
            raise NotFound("No saved recipe for " + key)
        if auth and not util.check_auth(recipe):
            raise Forbidden("Not authorised")
        # Allow some values to be overridden from request parameters
        for name in RECIPE_OVERRIDES:
            if args.get(name):
                recipe['overridden'] = True
                recipe['args'][name] = args.get(name)
    else:
        recipe = recipes.Recipe(args)

    return recipe

