"""
Persistent profile-storage module for the HXL Proxy

Started by David Megginson, February 2015
"""

import shelve
import base64
import hashlib
import random
import time

VERSION=1.0

from hxl_proxy import app

class Profile(object):

    def __init__(self, args):
        self.args = args
        self.version = 1.0

def make_profile(args):
    return Profile(args)

def get_profile(key):
    """
    Get an existing profile.
    @param key the string key for the profile.  
    @return the profile as an associative array.
    """
    key = str(key)
    dict = shelve.open(app.config['PROFILE_FILE'])
    try:
        if dict.has_key(key):
            return _check_profile(dict[key])
        else:
            return None
    finally:
        dict.close()

def update_profile(key, profile):
    """
    Update an existing profile.
    @param key the string key for the profile
    @param profile the profile as an associative array
    @return the key provided
    """
    dict = shelve.open(app.config['PROFILE_FILE'])
    try:
        dict[str(key)] = profile
        return key
    finally:
        dict.close()

def add_profile(profile):
    """
    Add a new profile.
    @param profile the profile as an associative array.
    @return the generated key for the new profile.
    """
    key = _gen_key()
    dict = shelve.open(app.config['PROFILE_FILE'])
    try:
        # check for collisions
        while dict.has_key(key):
            key = _gen_key()
        dict[str(key)] = _check_profile(profile)
        return key
    finally:
        dict.close()

def _gen_key():
    """
    Generate a pseudo-random, 6-character hash for use as a key.
    """
    hash = base64.urlsafe_b64encode(hashlib.md5(str(time.time() * random.random())).digest())
    return hash[:6]

def _check_profile(profile):
    """Auto-upgrade old profile format(s)."""
    try:
        version = profile.version
    except:
        profile = make_profile(profile)
    return profile

# end
