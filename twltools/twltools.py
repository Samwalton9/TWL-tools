# A good portion of this code is based on the Flask tutorial (http://flask.pocoo.org/docs/0.12/tutorial/)
#
# Copyright (c) 2017 Sam Walton and contributors
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

import os
import sqlite3
import flask
import gspread
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import datetime

app = flask.Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
	USERNAME='admin',
	PASSWORD='default' #TODO: Move this out to a secret username & password
))
app.config.from_envvar('TWLTOOLS_SETTINGS', silent=True)

@app.route('/')
def index():
	return flask.render_template('index.html')

@app.route('/periodicals', methods=['GET', 'POST'])
def periodicals():

	if flask.request.method == 'POST':
		if 'submit_proxy' in flask.request.form:
			ProxyNumbers().collect_proxy_data()
	try:
		results = open('periodicals_data', 'r').readlines()
	except FileNotFoundError:
		results = None

	return flask.render_template('periodicals.html', results=results)


# @app.route('/login', methods=['GET', 'POST'])
# def login():
# 	error = None
# 	if flask.request.method == 'POST':
# 		if flask.request.form['username'] != app.config['USERNAME']:
# 			error = 'Invalid username'
# 		elif flask.request.form['password'] != app.config['PASSWORD']:
# 			error = 'Invalid password'
# 		else:
# 			flask.session['logged in'] = True
# 			flask.flash('Logged in successfully')
# 			return flask.redirect(flask.url_for('index'))
# 	return flask.render_template('login.html', error=error)

# @app.route('/logout')
# def logout():
# 	flask.session.pop('logged_in', None)
# 	flask.flash('Logged out')
# 	return flask.redirect(flask.url_for('index'))

# This doesn't use numpy for any sensible reason.
class ProxyNumbers():

	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name('../client_secret.json', scope) # Login to Google
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

		data_output = ["Data generated: %s" % datetime.datetime.now().strftime("%d %B %Y at %H:%M"),
			"",
			"Total periodicals: %s" % len(current_periodicals),
			"Number of unique periodicals: %s" % num_periodicals,
			"Number of periodicals accessible by proxy: %s" % num_proxy,
			"Number of bundle periodicals: %s" % num_bundle]

		f = open('periodicals_data', 'w')
		for line in data_output:
			f.write(line + "\n")