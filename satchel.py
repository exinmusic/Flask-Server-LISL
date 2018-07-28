from oauth2client.service_account import ServiceAccountCredentials
import httplib2
from apiclient import discovery

# application secret, for securing sessions
appKey = ''
# twitch api key
twitchKey = ''

# Remote Mongodb URI Config
DB_NAME = "" 
DB_HOST = ""
DB_USER = "" 
DB_PASS = ""
uriMongo = "mongodb://"+DB_USER+":"+DB_PASS+"@"+DB_HOST+"-a0.mlab.com:33188,"+DB_HOST+"-a1.mlab.com:33188/"+DB_NAME+"?replicaSet=rs-"+DB_HOST


# Google OAuth 2.0 Auth Service
def google_api_service(srvcScp):
	scopes = ['https://www.googleapis.com/auth/'+srvcScp]
	# try loading credentials from deployment directory
	try:
		credentials = ServiceAccountCredentials.from_json_keyfile_name(
			'/var/www/sites/lisl_deploy/client_secrets.json', scopes)
	# load from local dev directory
	except:
		credentials = ServiceAccountCredentials.from_json_keyfile_name(
			'client_secrets.json', scopes)
	http = credentials.authorize(httplib2.Http())
	return discovery.build(srvcScp, 'v3', http=http)