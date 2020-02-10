import sys

#Expand Python classes path with your app's path
sys.path.insert(0, "/opt/permission_request_application/cgi-bin")

from permission_request_tool import app

#Put logging code (and imports) here ...

#Initialize WSGI app object
application = app
