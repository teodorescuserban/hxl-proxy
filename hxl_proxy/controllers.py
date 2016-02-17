"""
Controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import os
import sys
import copy
import base64
import urllib
import tempfile

import werkzeug
from werkzeug import secure_filename
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound

from flask import Response, flash, request, render_template, redirect, make_response, session, g, url_for

import hxl

from hxl_proxy import app, cache, dao
from hxl_proxy.util import urlquote, check_auth, make_data_url, make_cache_key, skip_cache_p, urlencode_utf8
from hxl_proxy.filters import setup_filters, MAX_FILTER_COUNT
from hxl_proxy.validate import do_validate
from hxl_proxy.hdx import get_hdx_datasets
from hxl_proxy.preview import PreviewFilter
from hxl_proxy.auth import get_hid_login_url, get_hid_user

#
# Error handling
#

@app.errorhandler(403)
def handle_forbidden(error):
    if g.user:
        flash("Not allowed to access {}".format(request.full_path))
        return redirect('/settings/user', 303)
    else:
        flash("Must be logged in to access {}".format(request.full_path))
        return redirect('/login?from={}'.format(urlquote(request.full_path)), 303)

def error(e):
    """Default error page."""
    if isinstance(e, IOError):
        # probably tried to open an inappropriate URL
        status = 403
    else:
        status = 500
    return render_template('error.html', e=e, category=type(e)), status

if not app.config.get('DEBUG'):
    # Register only if not in DEBUG mode
    app.register_error_handler(BaseException, error)


#
# Meta handlers
#

@app.before_request
def before_request():
    """Code to run immediately before the request"""
    app.secret_key = app.config['SECRET_KEY']
    request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
    if (session.get('user_id')):
        g.user = dao.UserDAO.read(session.get('user_id'))
    else:
        g.user = None

#
# Redirects for deprecated URL patterns
#

@app.route("/")
def redirect_home():
    # home isn't moved permanently
    return redirect("/data/source?" + urllib.parse.urlencode(request.args) , 302)

#
# Primary controllers
#

@app.route("/data/source")
@app.route("/data/<key>/source")
def show_data_source(key=None):
    """Choose a new data source."""
    recipe = dao.get_recipe(key, auth=True)
    return render_template('data-source.html', key=key, recipe=recipe)


@app.route("/data/tagger")
@app.route("/data/<key>/tagger")
def show_data_tag(key=None):
    """Add HXL tags to an untagged dataset."""
    recipe = dao.get_recipe(key, auth=True)

    header_row = request.args.get('header-row')
    if header_row:
        header_row = int(header_row)

    if not recipe.url:
        flash('Please choose a data source first.')
        return redirect(make_data_url(recipe, key, 'source'), 303)

    preview = []
    i = 0
    for row in hxl.io.make_input(recipe.url):
        if i >= 25:
            break
        else:
            i = i + 1
        if row:
            preview.append(row)
        
    return render_template('data-tagger.html', key=key, recipe=recipe, preview=preview, header_row=header_row)


@app.route("/data/edit")
@app.route("/data/<key>/edit", methods=['GET', 'POST'])
def show_data_edit(key=None):
    """Create or edit a filter pipeline."""
    recipe = dao.get_recipe(key, auth=True)

    if recipe.url:
        # show only a short preview
        try:
            source = PreviewFilter(setup_filters(recipe), max_rows=5)
            source.columns # force-trigger an exception if not tagged
        except:
            flash('No HXL tags found')
            return redirect(make_data_url(recipe, key, 'tagger'), 303)
    else:
        flash('Please choose a data source first.')
        return redirect(make_data_url(recipe, key, 'source'), 303)

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, MAX_FILTER_COUNT):
        if recipe.args.get('filter%02d' % n):
            filter_count = n
    if filter_count < MAX_FILTER_COUNT:
        filter_count += 1

    show_headers = (recipe.args.get('strip-headers') != 'on')

    return render_template('data-recipe.html', key=key, recipe=recipe, source=source, show_headers=show_headers, filter_count=filter_count)

@app.route("/data/recipe")
@app.route("/data/<key>/recipe")
def show_data_recipe(key=None):
    """Show form to save a recipe."""
    recipe = dao.get_recipe(key, auth=True)

    if not recipe or not recipe.url:
        return redirect('/data/source', 303)

    return render_template('data-about.html', key=key, recipe=recipe)

@app.route('/data/<key>/chart')
@app.route('/data/chart')
def show_data_chart(key=None):
    """Show a chart visualisation for the data."""
    recipe = dao.get_recipe(key)
    if not recipe or not recipe.url:
        return redirect('/data/source', 303)

    source = setup_filters(recipe)
    tag = request.args.get('tag')
    if tag:
        tag = hxl.TagPattern.parse(tag);
    label = request.args.get('label')
    if label:
        label = hxl.TagPattern.parse(label);
    type = request.args.get('type', 'bar')
    return render_template('visualise-chart.html', key=key, recipe=recipe, tag=tag, label=label, filter=filter, type=type, source=source)

@app.route('/data/<key>/map')
@app.route('/data/map')
def show_data_map(key=None):
    """Show a map visualisation for the data."""
    recipe = dao.get_recipe(key)
    if not recipe or not recipe.url:
        return redirect('/data/source', 303)
    layer_tag = hxl.TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('visualise-map.html', key=key, recipe=recipe, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<key>/validate")
def show_validate(key=None):
    """Validate the data."""

    # Get the recipe
    recipe = dao.get_recipe(key)
    if not recipe or not recipe.url:
        return redirect('/data/source', 303)

    severity_level = request.args.get('severity', 'info')
    detail_hash = request.args.get('details', None)

    # If we have a URL, validate the data.
    if recipe.url:
        errors = do_validate(setup_filters(recipe), recipe.schema_url, severity_level)

    return render_template('validate-summary.html', key=key, recipe=recipe, schema_url=recipe.schema_url, errors=errors, detail_hash=detail_hash, severity=severity_level)

@app.route("/data/<key>.<format>")
@app.route("/data/<key>/download/<stub>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/<key>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=make_cache_key, unless=skip_cache_p)
def show_data(key=None, format="html", stub=None):

    def get_result (key, format):
        recipe = dao.get_recipe(key, auth=False)
        if not recipe or not recipe.url:
            return redirect('/data/source', 303)

        source = setup_filters(recipe)
        show_headers = (recipe.args.get('strip-headers') != 'on')

        if format == 'html':
            return render_template('data-view.html', source=source, recipe=recipe, key=key, show_headers=show_headers)
        elif format == 'json':
            response = Response(list(source.gen_json(show_headers=show_headers)), mimetype='application/json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if hasattr(recipe, 'stub') and recipe.stub:
                response.headers['Content-Disposition'] = 'attachment; filename={}.json'.format(recipe.stub)
            return response
        else:
            response = Response(list(source.gen_csv(show_headers=show_headers)), mimetype='text/csv')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if hasattr(recipe, 'stub') and recipe.stub:
                response.headers['Content-Disposition'] = 'attachment; filename={}.csv'.format(recipe.stub)
            return response

    result = get_result(key, format)
    return result

@app.route("/actions/save-recipe", methods=['POST'])
def do_data_save():
    """
    Start a new saved pipeline, or update an existing one.

    Can be called from the full pipeline-edit form, or from
    the mini popup for a pipeline that the user is saving
    for the first time.
    """

    # We will have a key if we're updating an existing pipeline
    key = request.form.get('key')
    recipe = dao.get_recipe(key, auth=True, args=request.form)

    if not g.user:
        return redirect('/login?from={}'.format(make_data_url(recipe, key, 'recipe')))

    if key:
        recipe.from_args(request.form)
        dao.RecipeDAO.update(recipe)
    else:
        key = dao.RecipeDAO.create(recipe)

    # TODO be more specific about what we clear
    cache.clear()

    return redirect(make_data_url(recipe, key=key), 303)

@app.route('/settings/user')
def do_user_settings():
    if g.user:
        return render_template('settings-user.html', user=g.user, recipes=dao.RecipeDAO.list(g.user['user_id']))
    else:
        return redirect('/login', 303)

@app.route('/login')
def do_login():
    session['login_redirect'] = request.args.get('from', '/')
    return redirect(get_hid_login_url(), 303)

@app.route('/logout')
def do_logout():
    path = request.args.get('from', '/')
    session.clear()
    flash("Disconnected from your Humanitarian.ID account (browsing anonymously).")
    return redirect(path, 303)

@app.route('/oauth/authorized2/1')
def do_hid_authorisation():
    # now needs to submit the access token to H.ID to get more info
    code = request.args.get('code')
    state = request.args.get('state')
    if state != session.get('state'):
        raise Exception("Security violation: inconsistent state returned from humanitarian.id login request")
    else:
        session['state'] = None
    user_info = get_hid_user(code)
    redirect_path = session.get('login_redirect', '/')
    del session['login_redirect']

    user_id = user_info['user_id']
    session['user_id'] = user_id
    user = dao.UserDAO.read(user_id)
    if user:
        dao.UserDAO.update(user_info)
    else:
        dao.UserDAO.create(user_info)
    flash("Connected to your Humanitarian.ID account as {}".format(user_info.get('name')))
    return redirect(redirect_path, 303)

# end
