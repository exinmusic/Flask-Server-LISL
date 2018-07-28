![LOST IN SOUND dot LIVE](http://exin.pythonanywhere.com/static/lisl_little_dev_logo.png)

## Synopsis

The original application server for Lostinsound.Live. Based in python-flask, the server loads a page that then updates via ajax promises between clients the REST api on the server.

The main function of the server is to place a live stream video on the page given the stream is scheduled on a Google Calendar, and currently live on the 3rd party platform. 3rd parties include Twitch, and YouTube.

Auth0 is implemented for user auth.

## Setting Up the Local Dev Enviroment

This setup assumes Python 2.7, and pip are installed on the local machine (mac/linux).


#### Step 1: install VIRTUALENV  
```sudo pip install virtualenv```  
Virtualenv enables multiple side-by-side installations of Python, one for each project. It doesn’t actually install separate copies of Python, but it does provide a clever way to keep different project environments isolated. This is good practice, so as to keep different python versions and libraries with thier applications.

#### Step 2: change directory, create virtual enviroment 
```
cd <project folder>
virtualenv venv
```  
Make sure you're in the root directory of the project and run the command above to create a virual enviroment.

#### Step 3: activate enviroment 
```
. venv/bin/activate
```  
This will put python in the development enviroment that we can now setup. If you wish to return to your system enviroment simply enter the command `deactivate`. 

#### Step 4: install dependencies
```
pip install -r requirements.txt
```  
This will install the following dependencies
* requests
* Flask
* Flask-SSLify
* Flask-OAuthlib
* flask_cors
* oauth2client
* python-jose
* google-api-python-client
* six
* pymongo

#### Step 4: run flask
```
. lost_server
```  
Launch a server with the lost_server bash script.
