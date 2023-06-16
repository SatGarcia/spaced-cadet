"""
Module: setup-cookies.py

File to extract CSRF token from a HTTPie session file.
"""

import sys, json

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} [SESSION FILE]")
    sys.exit()

session_filename = sys.argv[1]


with open(session_filename, 'r') as session_file:
    session_data = json.load(session_file)

found_csrf = False

for cookie in session_data['cookies']:
    if cookie['name'] == "csrf_access_token":
        csrf_header = {'name': 'X-CSRF-TOKEN', 'value': cookie['value']}
        session_data["headers"].append(csrf_header)
        found_csrf = True

if not found_csrf:
    print("ERROR: Could not find csrf_access_token")

else:
    with open(session_filename, 'w') as session_file:
        json.dump(session_data, session_file)

