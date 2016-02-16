"""
Utility functions for hxl_proxy

Started 2015-02-18 by David Megginson
"""

import six
import re
import urllib
import datetime
import pickle
import re

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import url_for, request, flash, session, g, get_flashed_messages

import hxl

from hxl_proxy import app

CACHE_KEY_EXCLUDES = ['force']

def make_cache_key (path = None, args_in=None):
    """Make a key for a caching request, based on the full path."""
    if path is None:
        path = request.path
    if args_in is None:
        args_in = request.args
    args_out = {}
    for name in args_in:
        if name not in CACHE_KEY_EXCLUDES:
            args_out[name] = args_in[name]
    return path + pickle.dumps(args_out).decode('latin1')

def skip_cache_p ():
    """Test if we should skip the cache."""
    return True if (request.args.get('force') or (hasattr(g, 'user') and g.user) or get_flashed_messages()) else False

def strnorm (s):
    """Normalise a string"""
    return hxl.common.normalise_string(s)

def stream_template(template_name, **context):
    """From the flask docs - stream a long template result."""
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

def urlquote(value):
    return urllib.parse.quote_plus(value, safe='/')

def urlencode_utf8(params):
    if hasattr(params, 'items'):
        params = list(params.items())
    return '&'.join(
            urlquote(k) + '=' + urlquote(v) for k, v in params if v
    )

def using_tagger_p(profile):
    for name in profile['args']:
        if re.match(r'^tagger-', name):
            return True
    return False

def get_gravatar(email, size=40):
    import hashlib
    hash = hashlib.md5(email.encode('utf8').lower()).hexdigest()
    url = "http://www.gravatar.com/avatar/{hash}?s={size}".format(
        hash=hash,
        size=size
    )
    return url

PROFILE_OVERRIDES = ['url', 'schema_url']
PROFILE_ARGS_EXCLUDE = ['url', 'schema_url', 'stub', 'key', 'cloneable', 'format', 'filter_count', 'password', 'password-repeat', 'name', 'description']

def get_profile(key=None, auth=False, args=None):
    """Load a profile or create from args."""

    if args is None:
        args = request.args

    if key:
        #profile = dao.RecipeDAO.read(str(key))
        if not profile:
            raise NotFound("No saved profile for " + key)
        if auth and not check_auth(profile):
            raise Forbidden("Not authorised")
        # Allow some values to be overridden from request parameters
        for name in PROFILE_OVERRIDES:
            if args.get(name):
                profile['overridden'] = True
                profile['args'][name] = args.get(name)
    else:
        profile = { 'args': {} }

        # Copy args
        for name in args:
            profile['args'][name] = args[name]

        # Move up top-level properties
        for name in PROFILE_ARGS_EXCLUDE:
            if profile['args'].get(name):
                profile[name] = profile['args'][name]
                del profile['args'][name]

    return profile


def check_auth(profile):
    """Check authorisation."""
    if g.user and (g.user['user_id'] == profile['user_id']):
        return True
    else:
        return False

def add_args(extra_args):
    """Add GET parameters."""
    args = {}
    for key in request.args:
        args[key] = request.args[key]
    for key in extra_args:
        if extra_args[key]:
            # add keys with truthy values
            args[key] = extra_args[key]
        else:
            # remove keys with non-truthy values
            del args[key]
    return '?' + urlencode_utf8(args)

def make_data_url(profile=None, key=None, facet=None, format=None):
    """Construct a data URL for a profile."""
    url = None
    if key:
        url = '/data/' + urlquote(key)
        if facet:
            url += '/' + urlquote(facet)
        elif format:
            if hasattr(profile, 'stub') and profile.stub:
                url += '/download/' + urlquote(profile.stub) + '.' + urlquote(format)
            else:
                url += '.' + urlquote(format)
    else:
        url = '/data'
        if format:
            url += '.' + urlquote(format)
        elif facet:
            url += '/' + urlquote(facet)
        url += '?' + urlencode_utf8(profile['args'])

    return url

def severity_class(severity):
    """Return a CSS class for a validation error severity"""
    if severity == 'error':
        return 'severity_error'
    elif severity == 'warning':
        return 'severity_warning'
    else:
        return 'severity_info'

def re_search(regex, string):
    """Try matching a regular expression."""
    return re.search(regex, string)


#
# Declare Jinja2 filters and functions
#

app.jinja_env.filters['nonone'] = (
    lambda s: '' if s is None else s
)

app.jinja_env.filters['urlquote'] = (
    urlquote
)

app.jinja_env.filters['strnorm'] = (
    hxl.common.normalise_string
)

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

app.jinja_env.globals['using_tagger_p'] = (
    using_tagger_p
)

app.jinja_env.globals['add_args'] = (
    add_args
)

app.jinja_env.globals['data_url'] = (
    make_data_url
)

app.jinja_env.globals['severity_class'] = (
    severity_class
)

app.jinja_env.globals['re_search'] = (
    re_search
)

app.jinja_env.globals['get_gravatar'] = (
    get_gravatar
)

