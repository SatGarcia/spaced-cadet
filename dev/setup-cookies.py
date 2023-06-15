import sys, json

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} [SESSION FILE]")
    sys.exit()

session_filename = sys.argv[1]

found_atc = False
found_csrf = False

with open(session_filename, 'r') as session_file:
    session_data = json.load(session_file)

session_data['cookies'] = []

access_token_cookie = {
    "domain": "",
    "expires": None,
    "name": "access_token_cookie",
    "path": "/",
    "secure": False
}

csrf_access_token = {
    "domain": "",
    "expires": None,
    "name": "csrf_access_token",
    "path": "/",
    "secure": False
}

session_data['cookies'].append(access_token_cookie)
session_data['cookies'].append(csrf_access_token)


for line in sys.stdin:
    atc_loc = line.find("access_token_cookie=")
    if atc_loc >= 0:
        found_atc = True
        at_cookie = line[atc_loc:].split(';')[0]
        print(at_cookie)
        access_token_cookie['value'] = at_cookie.split('=')[1]

    csrf_loc = line.find("csrf_access_token=")
    if csrf_loc >= 0:
        found_csrf = True
        csrf_cookie = line[csrf_loc:].split(';')[0]
        print(csrf_cookie)

        csrf_access_token['value'] = csrf_cookie.split('=')[1]
        session_data["headers"]["X-CSRF-TOKEN"] = csrf_access_token['value']

if not found_atc:
    print("ERROR: Could not find access_token_cookie")

if not found_csrf:
    print("ERROR: Could not find csrf_access_token")

if found_atc and found_csrf:
    with open(session_filename, 'w') as session_file:
        json.dump(session_data, session_file)

