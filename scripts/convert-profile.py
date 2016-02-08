#!/usr/bin/python3
"""
Convert recipes from the old shelve to sqlite3
"""

import sys, sqlite3, shelve, json

#
# Usage
#
if len(sys.argv) != 3:
    print("Usage: convert-profile <shelve file> <sqlite3 file>")
    exit(2)

shelve_file = sys.argv[1]
sqlite3_file = sys.argv[2]


#
# Leave out old, leaky args, and any empty values
#
IGNORE_ARGS = ['key', 'cloneable', 'format', 'filter_count', 'password', 'password-repeat', 'name', 'description', 'schema_url']

def clean_args(args_in):
    """Clean the args"""
    args_out = {}
    for name in args_in:
        if name not in IGNORE_ARGS and args_in[name]:
            args_out[name] = args_in[name]
    return args_out


#
# Copy the args
#
shelf = shelve.open(shelve_file, 'r');

connection = sqlite3.connect(sqlite3_file);
cursor = connection.cursor()

cursor.execute('delete from Recipes')

user_id ='david.megginson@gmail.com_1448562216195'
    
for key in shelf:
    name = shelf[key].name or "Anonymous recipe"
    description = shelf[key].description
    cloneable = shelf[key].cloneable
    if hasattr(shelf[key], 'stub'):
        stub = shelf[key].stub
    else:
        stub = None
    args = shelf[key].args
    cursor.execute(
        "insert into Recipes "
        "(recipe_id, user_id, name, description, cloneable, stub, args, date_created, date_modified) "
        "values (?, ?, ?, ?, ?, ?, ?, date('now'), date('now'))",
        (key, user_id, name, description, cloneable, stub, json.dumps(clean_args(args)),)
    )
    
connection.commit()
connection.close()
shelf.close()

# end
