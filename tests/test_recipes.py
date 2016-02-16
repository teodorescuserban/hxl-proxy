"""
Unit tests for hxl_proxy.filters module
David Megginson
March 2015

License: Public Domain
"""

import unittest
from hxl_proxy.recipes import Recipe
from hxl_proxy.util import urlquote

class TestRecipe(unittest.TestCase):

    ARGS_IN = {
        'url': 'http://example.org/data.csv',
        'schema_url': 'http://example.org/schema.csv',
        'filter01': 'count',
        'count01_pattern': 'org'
    }

    def test_empty(self):
        recipe = Recipe()
        assert recipe.url is None
        assert len(recipe.args) == 0

    def test_conversion(self):
        recipe = Recipe(self.ARGS_IN)
        assert recipe.url == self.ARGS_IN['url']
        assert recipe.schema_url == self.ARGS_IN['schema_url']
        self.assertEqual(self.ARGS_IN, recipe.to_args())

    def test_query_string(self):
        recipe = Recipe(self.ARGS_IN)
        arg_list = []
        for name, value in sorted(self.ARGS_IN.items()):
            arg_list.append("{}={}".format(urlquote(name), urlquote(value)))
        self.assertEqual("&".join(arg_list), recipe.to_query_string())
