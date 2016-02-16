"""A data recipe"""

from hxl_proxy.util import urlquote

class Recipe(object):

    def __init__(self, args_in=None):
        """Construct a recipe.

        @param args_in: GET parameters for building the recipe
        """

        self.url = None
        """The URL of the source dataset."""

        self.schema_url = None
        """The URL of the default validation schema."""

        self.key = None
        """The key of the dataset (only if saved)"""

        self.name = None
        """The name of the recipe (only if saved)"""

        self.description = None
        """The description of the dataset (only if saved)"""

        self.args = {}
        """The dynamic parameters for filters, etc."""

        if args_in is not None:
            self.from_args(args_in)


    PROPERTY_ARGS = ['key', 'url', 'schema_url', 'name', 'description']

    def from_args(self, args_in):
        """Populate a recipe from GET or POST parameters
        @param args_in: a dict of parameters
        """
        recipe = Recipe()
        for name in self.PROPERTY_ARGS:
            setattr(self, name, args_in.get(name))
        for name, value in args_in.items():
            if name not in self.PROPERTY_ARGS:
                self.args[name] = value

        return self

    def to_args(self, include_save_props=False):
        args_out = {}
        for name, value in self.args.items():
            if name not in self.PROPERTY_ARGS:
                args_out[name] = value
        if include_save_props:
            for name in self.PROPERTY_ARGS:
                args_out[name] = getattr(self, name)
        else:
            args_out['url'] = self.url
            args_out['schema_url'] = self.schema_url
        return args_out
                
    def to_query_string(self, overrides={}):
        filtered_args = {}

        for name, value in self.to_args().items():
            if value:
                filtered_args[name] = value

        for name, value in overrides.items():
            if value:
                filtered_args[name] = value
            else:
                del filtered_args[name]

        return "&".join("{}={}".format(urlquote(name), urlquote(value)) for name, value in filtered_args.items())
        
