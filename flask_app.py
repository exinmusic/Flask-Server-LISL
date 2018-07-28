#Core Requirements
import requests
from flask import Flask, render_template, jsonify, Markup, session, request, url_for, flash, redirect, make_response
from flask_sslify import SSLify
from functools import wraps
from satchel import appKey, twitchKey, uriMongo, google_api_service
from time import time
import datetime
import re
import json
from pymongo import MongoClient
from flask_cors import cross_origin
from flask_cors import CORS
import platform

#Auth0 Requirements
from flask_oauthlib.client import OAuth
from six.moves.urllib.parse import urlencode
from six.moves.urllib.request import urlopen
from urllib import quote as percEnc
from jose import jwt

# APP SETUP
app = Flask(__name__)
sslify = SSLify(app, permanent=True)
oauth = OAuth(app)
app.secret_key = appKey
cors = CORS(app, resources={r"/*": {"origins": "*"}})

# API BUFFER OBJECT
apiBufferObj = {'timestamp':0}
bufferLifetime = 10

# TWITCH API VARIABLES
streamsTwitch = 'https://api.twitch.tv/kraken/streams/'
clientTwitch = '?client_id=' + twitchKey

# INITIALIZE OAUTHLIB
auth0 = oauth.remote_app(
	'auth0',
	consumer_key='',
	consumer_secret='',
	request_token_params={
		'scope': 'openid profile user_metadata',
		'audience': 'https://' + 'lostinsoundlive.auth0.com' + '/userinfo'
	},
	base_url='https://%s' % 'lostinsoundlive.auth0.com',
	access_token_method='POST',
	access_token_url='/oauth/token',
	authorize_url='/authorize',
)

# AUTH0 CALLBACK HANDLER
@app.route('/callback')
def callback_handling():
	# Handles response from token endpoint
	resp = auth0.authorized_response()

	if resp is None:
		raise Exception('Access denied: reason=%s error=%s' % (
			request.args['error_reason'],
			request.args['error_description']
		))

	# Obtain JWT and the keys to validate the signature
	id_token = resp['id_token']
	jwks = urlopen("https://"+"lostinsoundlive.auth0.com"+"/.well-known/jwks.json")

	payload = jwt.decode(id_token, jwks.read(), algorithms=['RS256'], audience="", issuer="https://"+"lostinsoundlive.auth0.com"+"/")

	# Store the user information obtained in the id_token in flask session.
	session['jwt_payload'] = payload

	session['profile'] = {
		'user_id': payload['sub'],
		'name': payload['https://lostinsound.live/user_metadata']['lislName'],
		'picture': payload['picture'],
		'email' : payload['name'],
		'chatColor': payload['https://lostinsound.live/user_metadata']['chatColor']
	}
	return redirect('/')

# LOGIN REQUIRED
def login_required(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		if 'profile' not in session:
			return redirect('/login')
		return f(*args, **kwargs)
	return decorated

# LOGIN
@app.route('/login')
def login():
	app.logger.info(platform.release()[-3:])
	# Determains where the server is running to tell auth0 where to callback.
	if platform.release()[-3:] == 'aws':
		return auth0.authorize(callback='https://www.lostinsound.live/callback')
	else:
		return auth0.authorize(callback='http://127.0.0.1:5000/callback')

# LOGOUT
@app.route('/logout')
def logout():
	# Clear session stored data
	session.clear()
	# Redirect user to logout endpoint
	params = {'returnTo': url_for('login', _external=True), 'client_id': ""}
	return redirect(auth0.base_url + '/v2/logout?' + urlencode(params))

# STREAM HANDLER
@app.route('/api/handler')
@cross_origin()
def api_handler():
	global apiBufferObj
	global bufferLifetime
	next5 = []

	# If buffer is still alive, return apiBufferObj.
	if time()-apiBufferObj['timestamp'] < bufferLifetime:
		returnedBufferObj = dict(apiBufferObj)
		del returnedBufferObj['timestamp']
		app.logger.info('API HANDLER RETURNED FROM: apiBufferObj')
		return jsonify(returnedBufferObj)

	# If buffer is not alive, start querying 3rd parties.
	else:
		# Connect to Google Cal API
		service = google_api_service('calendar')
		# Check the current time in UTC and store as 'now'.
		now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
		# Create a list of 0-5 events from Calendar API.
		eventsResult = service.events().list(
			calendarId='primary', timeMin=now, maxResults=5, singleEvents=True,
			orderBy='startTime').execute()
		eventsResultItems = eventsResult.get('items', [])
		# If calendar has atleast one event, determine when its scheduled.
		if eventsResultItems:
			# Format results
			events = []
			for event in eventsResultItems:
				start = event['start'].get('dateTime', event['start'].get('date'))
				eventSet = [str(event['summary']),start,str(event['description'])]
				events.append(eventSet)
			# Get next (possibly current) streamers name, date/time, and decription(json).
			try:
				eventObj = json.loads(events[0][2])
				nameOnPlatform, scheduledTime = eventObj['general']['streamer'], events[0][1]
			except:
				return "DELIMITER ERROR: please check calendar for hyperlinks..."
			# Create list of upcoming streams with name and date/time.
			for eachEvent in events:
				form_payload = json.loads(eachEvent[2])
				try:
					next5.append([eachEvent[0],eachEvent[1],form_payload['options']['flyer'],form_payload['options']['fbEvent']])
				except:
					next5.append([eachEvent[0],eachEvent[1]])
			# If the scheduled stream should be live, determine platform.
			if scheduledTime < now:
				# If the platform is Twitch, query and parse.
				if eventObj['general']['platform'] == 'twitch':
					twitch_endpoint = streamsTwitch + nameOnPlatform + clientTwitch
					r = requests.get(twitch_endpoint, timeout=None)
					twitch = r.json()
					liveShow = twitch['stream']
					# If a live stream is listed, gather details.
					if liveShow:
						# Create the platform object.
						showObj = {"id":"show"}
						showObj['title'] = twitch['stream']['channel']['status']
						showObj['name'] = nameOnPlatform
						showObj['avatar'] = twitch['stream']['channel']['logo']
						showObj['videoEmbed'] = "https://player.twitch.tv/?channel={0}".format(nameOnPlatform)
						showObj['chatEmbed'] = "https://www.twitch.tv/embed/{0}/chat".format(nameOnPlatform)

				# If the platform is Youtube, query and parse.
				elif eventObj['general']['platform'] == 'youtube':
					service = google_api_service('youtube')
					response = service.search().list(part="snippet", type="channel", q=nameOnPlatform, maxResults=1).execute()
					youTubeID = response.get('items', [])
					response = service.search().list(
					part= 'snippet',
					type= 'video',
					eventType= 'live',
					channelId= youTubeID[0]['id']['channelId'],
					maxResults=1,
					order= 'date').execute()
					youtube = response.get('items', [])
					liveShow = youtube
					# If a live stream is listed, gather details.
					if liveShow:
						# Create the platform object.
						showObj = {"id":"show"}
						showObj['title'] = youtube[0]['snippet']['title']
						showObj['videoId'] = youtube[0]['id']['videoId']
						showObj['name'] = nameOnPlatform
						showObj['avatar']= youtube[0]['snippet']['thumbnails']['default']['url']
				# If a live stream is listed, remove it from the next5 list and start to determine output.
				if liveShow:
					next5.pop(0)

		# Ensure that there arent more than 4 items
		while len(next5) > 4:
			next5.pop()

		# If the events object exists, add upcoming events to it.
		if 'eventObj' in locals():
			eventObj['general']['upcoming'] = next5
			# If a platform object exists, add it to the event object.
			if 'showObj' in locals():
				eventObj['general']['show'] = showObj
			else:
				del eventObj['options']
				del eventObj['general']['streamer']
				del eventObj['general']['platform']
				del eventObj['general']['format']
				del eventObj['general']['skill']
		else:
			eventObj={"general":{"id":"general", "upcoming":next5}}
		# Update buffer object.
		apiBufferObj = dict(eventObj)
		apiBufferObj['timestamp'] = time()
		app.logger.info('API HANDLER RETURNED FROM: 3rd Party')
		# Return object with appened info.
		return jsonify(eventObj)


# USER INFO
@app.route('/api/user', methods=['GET', 'POST'])
@cross_origin()
@login_required
def api_user():
	return jsonify(profileName=session['profile']['name'], profilePicture=session['profile']['picture'], profileEmail=session['profile']['email'], chatColor=session['profile']['chatColor'])


# INDEX
@app.route('/')
@login_required
def index():
	return render_template("index.html", profileName=session['profile']['name'], profilePicture=session['profile']['picture'], chatColor=session['profile']['chatColor'])