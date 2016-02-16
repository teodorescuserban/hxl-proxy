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
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import Response, flash, request, render_template, redirect, make_response, session, g, url_for

import hxl

from hxl_proxy import app, cache, dao
from hxl_proxy.util import get_profile, check_auth, make_data_url, make_cache_key, skip_cache_p, urlencode_utf8
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
        return redirect('/login?from={}'.format(urlquote(request.full_path), 303))

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
        g.user = dao.Users.read(session.get('user_id'))
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
    profile = get_profile(key, auth=True)
    return render_template('data-source.html', key=key, profile=profile)


@app.route("/data/tagger")
@app.route("/data/<key>/tagger")
def show_data_tag(key=None):
    """Add HXL tags to an untagged dataset."""
    profile = get_profile(key, auth=True)

    header_row = request.args.get('header-row')
    if header_row:
        header_row = int(header_row)

    if not profile.get('url'):
        flash('Please choose a data source first.')
        return redirect(make_data_url(profile, key, 'source'), 303)

    preview = []
    i = 0
    for row in hxl.io.make_input(profile.get('url')):
        if i >= 25:
            break
        else:
            i = i + 1
        if row:
            preview.append(row)
        
    return render_template('data-tagger.html', key=key, profile=profile, preview=preview, header_row=header_row)


@app.route("/data/edit")
@app.route("/data/<key>/edit", methods=['GET', 'POST'])
def show_data_edit(key=None):
    """Create or edit a filter pipeline."""
    profile = get_profile(key, auth=True)

    if profile.get('url'):
        # show only a short preview
        try:
            source = PreviewFilter(setup_filters(profile), max_rows=5)
            source.columns # force-trigger an exception if not tagged
        except:
            flash('No HXL tags found')
            return redirect(make_data_url(profile, key, 'tagger'), 303)
    else:
        flash('Please choose a data source first.')
        return redirect(make_data_url(profile, key, 'source'), 303)

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, MAX_FILTER_COUNT):
        if profile['args'].get('filter%02d' % n):
            filter_count = n
    if filter_count < MAX_FILTER_COUNT:
        filter_count += 1

    show_headers = (profile['args'].get('strip-headers') != 'on')

    return render_template('data-recipe.html', key=key, profile=profile, source=source, show_headers=show_headers, filter_count=filter_count)

@app.route("/data/profile")
@app.route("/data/<key>/profile")
def show_data_profile(key=None):
    """Show form to save a profile."""
    profile = get_profile(key, auth=True)

    if not profile or not profile.get('url'):
        return redirect('/data/source', 303)

    return render_template('data-about.html', key=key, profile=profile)

@app.route('/data/<key>/chart')
@app.route('/data/chart')
def show_data_chart(key=None):
    """Show a chart visualisation for the data."""
    profile = get_profile(key)
    if not profile or not profile.get('url'):
        return redirect('/data/source', 303)

    source = setup_filters(profile)
    tag = request.args.get('tag')
    if tag:
        tag = hxl.TagPattern.parse(tag);
    label = request.args.get('label')
    if label:
        label = hxl.TagPattern.parse(label);
    type = request.args.get('type', 'bar')
    return render_template('visualise-chart.html', key=key, profile=profile, tag=tag, label=label, filter=filter, type=type, source=source)

@app.route('/data/<key>/map')
@app.route('/data/map')
def show_data_map(key=None):
    """Show a map visualisation for the data."""
    profile = get_profile(key)
    if not profile or not profile.get('url'):
        return redirect('/data/source', 303)
    layer_tag = hxl.TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('visualise-map.html', key=key, profile=profile, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<key>/validate")
def show_validate(key=None):
    """Validate the data."""

    # Get the profile
    profile = get_profile(key)
    if not profile or not profile.get('url'):
        return redirect('/data/source', 303)

    # Get the parameters
    url = profile.get('url')
    if request.args.get('schema_url'):
        schema_url = request.args.get('schema_url', None)
    else:
        schema_url = profile['args'].get('schema_url', None)

    severity_level = request.args.get('severity', 'info')

    detail_hash = request.args.get('details', None)

    # If we have a URL, validate the data.
    if url:
        errors = do_validate(setup_filters(profile), schema_url, severity_level)

    return render_template('validate-summary.html', key=key, profile=profile, schema_url=schema_url, errors=errors, detail_hash=detail_hash, severity=severity_level)

@app.route("/data/<key>.<format>")
@app.route("/data/<key>/download/<stub>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/<key>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=make_cache_key, unless=skip_cache_p)
def show_data(key=None, format="html", stub=None):

    def get_result (key, format):
        profile = get_profile(key, auth=False)
        if not profile or not profile.get('url'):
            return redirect('/data/source', 303)

        source = setup_filters(profile)
        show_headers = (profile['args'].get('strip-headers') != 'on')

        if format == 'html':
            return render_template('data-view.html', source=source, profile=profile, key=key, show_headers=show_headers)
        elif format == 'json':
            response = Response(list(source.gen_json(show_headers=show_headers)), mimetype='application/json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if hasattr(profile, 'stub') and profile.stub:
                response.headers['Content-Disposition'] = 'attachment; filename={}.json'.format(profile.stub)
            return response
        else:
            response = Response(list(source.gen_csv(show_headers=show_headers)), mimetype='text/csv')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if hasattr(profile, 'stub') and profile.stub:
                response.headers['Content-Disposition'] = 'attachment; filename={}.csv'.format(profile.stub)
            return response

    result = get_result(key, format)
    return result

@app.route("/actions/save-profile", methods=['POST'])
def do_data_save():
    """
    Start a new saved pipeline, or update an existing one.

    Can be called from the full pipeline-edit form, or from
    the mini popup for a pipeline that the user is saving
    for the first time.
    """

    # We will have a key if we're updating an existing pipeline
    key = request.form.get('key')
    profile = get_profile(key, auth=True, args=request.form)

    # Update profile metadata
    if 'name' in request.form:
        profile.name = request.form['name']
    if 'description' in request.form:
        profile.description = request.form['description']
    if 'cloneable' in request.form:
        profile.cloneable = (request.form['cloneable'] == 'on')
    if 'stub' in request.form:
        profile.stub = request.form['stub']

    # merge args
    profile['args'] = {}
    for name in request.form:
        if request.form.get(name) and name not in BLACKLIST:
            profile['args'][name] = request.form.get(name)

    # check for a password change
    password = request.form.get('password')
    password_repeat = request.form.get('password-repeat')

    if key:
        # Updating an existing profile.
        if password:
            if password == password_repeat:
                profile.set_password(password)
            else:
                raise BadRequest("Passwords don't match")
        g.profiles.update_profile(str(key), profile)
    else:
        # Creating a new profile.
        if password == password_repeat:
            profile.set_password(password)
        else:
            raise BadRequest("Passwords don't match")
        key = g.profiles.add_profile(profile)
        # FIXME other auth information is in __init__.py
        session['passhash'] = profile.passhash

    # TODO be more specific about what we clear
    cache.clear()

    return redirect(make_data_url(profile, key=key), 303)

@app.route('/settings/user')
def do_user_settings():
    if g.user:
        return render_template('settings-user.html', user=g.user, recipes=dao.Recipes.list(g.user['user_id']))
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
    user = dao.Users.read(user_id)
    if user:
        dao.Users.update(user_info)
    else:
        dao.Users.create(user_info)
    flash("Connected to your Humanitarian.ID account as {}".format(user_info.get('name')))
    return redirect(redirect_path, 303)

# end
