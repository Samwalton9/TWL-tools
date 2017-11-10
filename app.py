# A good portion of this code is based on the Flask tutorial (http://flask.pocoo.org/docs/0.12/tutorial/)
# and flask-login tutorial (https://github.com/maxcountryman/flask-login)
#
# Copyright (c) 2017 Wikimedia Foundation, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import flask
import flask_login
import os
import gspread
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from fnmatch import fnmatch

app = flask.Flask(__name__)
app.config.from_object(__name__)

app.config.from_envvar('TWLTOOLS_SETTINGS', silent=True)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

__dir__ = os.path.dirname(__file__)

loaded_password = open(os.path.join(__dir__,'site_password')).readline().strip()

users = {'admin':{'password': loaded_password}}

app.secret_key = open(os.path.join(__dir__,'secret_key')).readline().strip()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def load_user(username):
	if username not in users:
		return None
	
	user = User()
	user.id = username
	return user

@login_manager.request_loader
def request_loader(request):
	username = request.form.get('username')
	if username not in users:
		return None

	user = User()
	user.id = username

	return user

@app.route('/')
def index():
	return flask.render_template('index.html')

@app.route('/periodicals', methods=['GET', 'POST'])
@flask_login.login_required
def periodicals():

	if flask.request.method == 'POST':
		if 'submit_proxy' in flask.request.form:
			ProxyNumbers().collect_proxy_data()
	try:
		results = open('periodicals_data', 'r').readlines()
	except FileNotFoundError:
		results = None

	return flask.render_template('periodicals.html', results=results)

@app.route('/pageviews')
@flask_login.login_required
def pageviews():

	logs_list = list_logs(os.path.join(__dir__,"logs/"),"*.txt")

	if len(logs_list) > 0: #Check this works if 0 files present
		simple_list = sorted(["_".join(i.split("_")[:3]) 
							for i in logs_list 
							if 'latest' not in i])
		simple_list.insert(0, 'latest')

	return flask.render_template('pageviews.html', results=simple_list, type='files')


@app.route('/pageviews/<log_file>')
@flask_login.login_required
def individual_log(log_file):
	results = open('logs/%s_pageviews_log.txt' % log_file, 'r').readlines()

	return flask.render_template('pageviews.html', results=results, type='log')

@app.route('/login', methods=['GET', 'POST'])
def login():

	if flask.request.method == 'POST':
		username = flask.request.form['username']
		if username in users:
			if flask.request.form['password'] == users[username]['password']:
				user = User()
				user.id = username
				flask_login.login_user(user)
				flask.flash('Logged in successfully')
				return flask.redirect(flask.url_for('index'))
			else:
				error_msg = 'Incorrect password'
				return flask.render_template('login.html', error=error_msg)
		else:
			error_msg = 'Incorrect username'
			return flask.render_template('login.html', error=error_msg)
	
	return flask.render_template('login.html')

@app.route('/logout')
@flask_login.login_required
def logout():
	flask_login.logout_user()
	flask.flash('Logged out successfully')
	return flask.redirect(flask.url_for('index'))

def list_logs(log_directory, file_pattern):
	final_list = []
	file_list = os.listdir(log_directory)
	for log_file in file_list:
		if fnmatch(log_file, file_pattern):
			final_list.append(log_file)
	return final_list

#TODO: Move into a separate file, split out some code that's duplicated elsewhere
class ProxyNumbers():

	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope) # Login to Google
	g_client = gspread.authorize(creds)

	def get_worksheet(self, key, sheet_num):
		# Return a worksheet given a sheet key and tab number
		g_sheet = self.g_client.open_by_key(key)
		worksheet = g_sheet.get_worksheet(sheet_num)

		return worksheet

	def gen_partner_list(self, access_method):
		# Returns a list of partners that said 'Yes' to proxy or bundle
		columns = {'proxy': 8, 'bundle': 9}

		authentication_sheet = self.get_worksheet('1BCldgV2ny6YOlubciOB2dzhGlKJiWgNQVa3FLTG0180', 0)
		partner_names = list(filter(None,authentication_sheet.col_values(1)))[1:]
		num_partners = len(partner_names)

		# Sheet has more rows than partners, so ignore all the blank cells at the end of the column
		decision = authentication_sheet.col_values(columns[access_method])[1:num_partners+1]

		return np.array(partner_names)[np.array(decision) == 'Yes']

	def unique_if_partner(self, partners, periodicals, partner_shortlist):
		# Return unique periodicals from a shortlist of bundle or proxy periodicals
		return np.unique([i for j, i in enumerate(periodicals) if partners[j] in partner_shortlist])

	def get_data(self):
	# Pull A-Z list (periodicals and partners) from Wikipedia Library A-Z Sources Search Google Sheet
		az_sheet = self.get_worksheet('1ndJiMkWvsKpEXZpE5m6bFFgJHulD3M9gDpIIfe-LsKU', 1)

		periodicals = np.array(list(filter(None,az_sheet.col_values(1))))
		partners = np.array(list(filter(None,az_sheet.col_values(2))))

		# EBSCO is listed per collection name in A-Z sheet (e.g. EBSCO: MasterFILE Complete)
		# So do a quick search for EBSCO collections and call them all 'EBSCO'
		for l, partner in enumerate(partners):
			if "EBSCO" in partner:
				partners[l] = "EBSCO"

		return partners, periodicals

	def collect_proxy_data(self):

		proxy_partners = self.gen_partner_list('proxy')
		bundle_partners = self.gen_partner_list('bundle')

		current_partners, current_periodicals = self.get_data()

		unique_bundle = self.unique_if_partner(current_partners, current_periodicals, bundle_partners)
		unique_proxy = self.unique_if_partner(current_partners, current_periodicals, proxy_partners)
		proxy_no_bundle = len(unique_proxy) - len(unique_bundle)

		num_bundle, num_proxy, num_periodicals = len(unique_bundle), len(unique_proxy), len(np.unique(current_periodicals))

		data_output = ["Data generated: %s (UTC)" % datetime.datetime.now().strftime("%d %B %Y at %H:%M"),
			"",
			"Total periodicals: %s" % len(current_periodicals),
			"Number of unique periodicals: %s" % num_periodicals,
			"Number of periodicals accessible by proxy: %s (%.1f%%)" % (num_proxy, 100 * (num_proxy/num_periodicals)),
			"Number of bundle periodicals: %s (%.1f%%)" % (num_bundle, 100 * (num_bundle/num_periodicals))]

		f = open('periodicals_data', 'w')
		for line in data_output:
			f.write(line + "\n")
