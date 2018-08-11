import webapp2

import cgi
import jinja2
import os

import requests
import requests.auth
import requests_toolbelt.adapters.appengine

from uuid import uuid4
import urllib

import json

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir))

CLIENT_ID = "580697bb9af279a4e7dc"
CLIENT_SECRET = "686dea2590e177bca9343ce80c97d8d3da44e289"
REDIRECT_URI = "http://localhost:8080/callback"
STATE = ""

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainPage(Handler):

    def make_authorization_url(self):
        state = str(uuid4())
        STATE = state
        params = {
            "client_id": CLIENT_ID,
			"redirect_uri": REDIRECT_URI,
			"state": state,
			"scope": "repo"
            }
        url = "https://github.com/login/oauth/authorize?" + urllib.urlencode(params)
        return url

    def get(self):

        requests_toolbelt.adapters.appengine.monkeypatch()
        loginurl = self.make_authorization_url()
        self.render("index.html", loginurl=loginurl)

class Callback(Handler):

    global access_token
    
    def get_token(self, code):
        post_data = {
                     "client_id":CLIENT_ID,
                     "client_secret":CLIENT_SECRET,
		    		 "code": code,
			    	 "redirect_uri": REDIRECT_URI,
                     "state": STATE
                     }
        response = requests.post("https://github.com/login/oauth/access_token?", data=post_data)
        resp = response.content.split('&')[0]
        return resp.split('=')[1]

    def get(self):

        requests_toolbelt.adapters.appengine.monkeypatch()
        error = self.request.get('error')
        state = self.request.get('state')
        code = self.request.get('code')
        access_token = self.get_token(code)
        self.redirect("/home?access_token="+access_token)

class home(Handler):
    
    def get(self):
        requests_toolbelt.adapters.appengine.monkeypatch()
        access_token = self.request.get("access_token")

        token = 'token %s' % access_token
        print("token")
        print(token)
        self.headers = {"Authorization": token}
        response = requests.get("https://api.github.com/user/repos", headers=self.headers)

        dumpcard = []

        content = json.loads(response.content)

        i = 0
        for c in content:
            temp = {}
            temp['url'] = c['svn_url']
            temp['name'] = c['name']
            temp['open_issues'] = int(c['open_issues'])
            temp['forks'] = int(c['forks'])
            temp['score'] = (temp['forks'] + temp['open_issues']) / 2
            i += 1
            dumpcard.append(temp)

        newlist = sorted(dumpcard, key=lambda k: k['score'])

        self.render("home.html", content=newlist)


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/callback', Callback),
    ('/home', home)
    ], debug=True)