"""
Base classes for HXL Proxy unit tests.
David Megginson
December 2015

License: Public Domain
"""

import unittest
import os
import tempfile

import hxl_proxy


class BaseControllerTest(unittest.TestCase):
    """Base class for controller tests."""
    
    DB_SCRIPT = os.path.join(os.path.dirname(__file__), 'test-data.sql')

    def setUp(self):
        hxl_proxy.app.config['DEBUG'] = False
        hxl_proxy.app.config['DB_FILE'] = ':memory:'
        hxl_proxy.app.config['SECRET_KEY'] = 'abcde'
        hxl_proxy.app.config['HID_BASE_URL'] = 'https://hid.example.org'
        hxl_proxy.app.config['HID_CLIENT_ID'] = '12345'
        hxl_proxy.app.config['HID_REDIRECT_URI'] = 'https://proxy.example.org'

        # create an empty database
        with hxl_proxy.app.test_request_context('/'):
            hxl_proxy.dao.create_db()
            hxl_proxy.dao._executefile(self.DB_SCRIPT)

        #self.key = RecipeManager(self.filename).add_recipe(self.make_recipe())
        self.key = 'AAAAA'
        self.client = hxl_proxy.app.test_client()

        
    def tearDown(self):
        """Remove the temporary recipe database"""
        pass
    
    def get(self, path, params=None, status=200):
        """
        Send a request to the test client and hang onto the result.
        @param path the path to request
        @param params (optional) a dict of get parameters
        @param status (optional) the expected HTTP status (defaults to 200)
        @return a Response object
        """
        self.response = self.client.get(path, query_string=params)
        self.assertEqual(status, self.response.status_code)
        return self.response

    def assertBasicDataset(self, response=None):
        """Check that we're looking at the basic dataset"""
        if response is None:
            response = self.response
        self.assertEqual(200, response.status_code)
        assert b'Country' in response.data
        assert b'#country' in response.data
        assert b'Org A' in response.data
        assert b'Education' in response.data
        assert b'Myanmar' in response.data

    @staticmethod
    def make_recipe():
        recipe = Recipe({
            'url': 'http://example.org/basic-dataset.csv'
        })
        recipe.name = 'Sample dataset'
        return recipe


