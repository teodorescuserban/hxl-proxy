"""Logic for data recipes, including conversion from representations."""

import json
from hxl_proxy.util import urlquote

class Recipe(object):
    """A data recipe."""

    PROPERTY_ARGS = ['key', 'url', 'schema_url', 'name', 'description', 'stub', 'cloneable']
    """Arguments that should become object properties."""

    def __init__(self, args_in=None, db_in=None):
        """Construct a recipe.
        @param args_in: dict of HTTP-style parameters for building the recipe (default: None)
        @param db_in: dict of SQL-style values for building the recipe (default: None)
        """

        self.url = None
        """The URL of the source dataset."""

        self.schema_url = None
        """The URL of the default validation schema."""

        self.owner_id = None
        """The user id for the owner (only if saved)"""
        
        self.key = None
        """The key of the dataset (only if saved)"""

        self.name = None
        """The name of the recipe (only if saved)"""

        self.description = None
        """The description of the dataset (only if saved)"""

        self.stub = ''
        """The download filename stub (only if saved)"""

        self.cloneable = True
        """Are users allowed to clone this recipe? (only if saved)"""

        self.args = {}
        """The dynamic parameters for filters, etc."""

        self.overridden = False
        """True if this recipe has been overridden by request parameters"""

        # Initialise if we have starting data
        if args_in is not None:
            # initialise from HTTP-style parameters
            self.from_args(args_in)
        elif db_in is not None:
            # initialise from SQL-style parameters
            self.from_db(db_in)

    def from_args(self, args_in):
        """Populate a recipe from HTTP-style parameters
        @param args_in: a dict of parameters
        @return: this object
        """
        recipe = Recipe()
        for name in self.PROPERTY_ARGS:
            setattr(self, name, args_in.get(name))
        for name, value in args_in.items():
            if name not in self.PROPERTY_ARGS:
                self.args[name] = value

        return self

    def to_args(self):
        """Generate a dict of HTTP-style parameters
        """
        args_out = {}
        for name, value in self.args.items():
            if name not in self.PROPERTY_ARGS:
                args_out[name] = value
        for name in self.PROPERTY_ARGS:
            args_out[name] = getattr(self, name)
        return args_out

    def from_db(self, db_in):
        """Populate a recipe from a SQL data row.
        @param db_in: a dict of SQL-style values
        @return: this object
        """
        db_in = dict(db_in) # FIXME why do we crash without this?
        for name in db_in:
            if name in self.PROPERTY_ARGS:
                setattr(self, name, db_in.get(name))
        self.owner_id = db_in.get('user_id')
        self.key = db_in.get('recipe_id')
        self.args = json.loads(db_in.get('args'))
        return self
                
    def to_query_string(self, overrides={}):
        """Generate a URL-encoded parameter string.
        @param overrides: a dict of values to replace (False values mean remove the parameter)
        @return: a URL-encode query string
        """
        filtered_args = {}

        for name, value in self.to_args().items():
            if value:
                filtered_args[name] = value

        for name, value in overrides.items():
            if value:
                filtered_args[name] = value
            else:
                del filtered_args[name]

        return "&".join("{}={}".format(urlquote(name), urlquote(value)) for name, value in sorted(filtered_args.items()))
        
