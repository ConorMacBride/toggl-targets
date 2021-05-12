#!/usr/bin/env python

# Load requirements
import sys
import requests
from requests.auth import HTTPBasicAuth

# Get Toggl API Token
try:
    API_TOKEN = str(sys.argv[1])
except (ValueError, IndexError) as e:
    print("Toggl API token must be provided!")
    sys.exit(1)

url = 'https://api.track.toggl.com/api/v8/workspaces'
headers = {'content-type': 'application/json'}

# Get workspace
r = requests.get(url, headers=headers, auth=HTTPBasicAuth(API_TOKEN, 'api_token'))
r.raise_for_status()  # Check if there was an error

workspaces = r.json()

print("Select the workplace:")
i = 0
for workspace in workspaces:
    i += 1
    print(i, ':', workspace['name'])

try:
    wid = int(input())
    assert 1 <= wid <= i
except (ValueError, AssertionError) as e:
    print("ERROR: Bad choice.")
    sys.exit(1)

# Get project
r = requests.get(url + '/' + str(workspaces[wid-1]['id']) + '/projects',
                 headers=headers, auth=HTTPBasicAuth(API_TOKEN, 'api_token'))
r.raise_for_status()  # Check if there was an error

projects = r.json()

print("Project ID")
for project in projects:
    print(project['id'], project['name'])
