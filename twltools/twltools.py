import os
import sqlite3
import flask
import gspread
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials

app = flask.Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
	USERNAME='admin',
	PASSWORD='default' #TODO: Move this out to a secret username & password
))
app.config.from_envvar('TWLTOOLS_SETTINGS', silent=True)

@app.route('/')
def index():
	results = None
	if flask.request.method == 'POST':
		if flask.request.form['submit'] == 'proxy':
			results = proxy_numbers.collect_data()
		if flask.request.form['submit'] == 'metrics':
			pass #Figure out how to run, print progress(?), and output
		else:
			pass #This should never happen, so not sure what goes here

	return flask.render_template('index.html', results=results)

@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	if flask.request.method == 'POST':
		if flask.request.form['username'] != app.config['USERNAME']:
			error = 'Invalid username'
		elif flask.request.form['password'] != app.config['PASSWORD']:
			error = 'Invalid password'
		else:
			flask.session['logged in'] = True
			flask.flash('Logged in successfully')
			return flask.redirect(flask.url_for('index'))
	return flask.render_template('login.html', error=error)

@app.route('/logout')
def logout():
	flask.session.pop('logged_in', None)
	flask.flash('Logged out')
	return flask.redirect(flask.url_for('index'))

#
# proxy_numbers.py
#

def get_worksheet(key, sheet_num):
	# Return a worksheet given a sheet key and tab number
	g_sheet = g_client.open_by_key(key)
	worksheet = g_sheet.get_worksheet(sheet_num)

	return worksheet

def gen_partner_list(access_method):
	# Returns a list of partners that said 'Yes' to proxy or bundle
	columns = {'proxy': 8, 'bundle': 9}

	authentication_sheet = get_worksheet('1BCldgV2ny6YOlubciOB2dzhGlKJiWgNQVa3FLTG0180', 0)
	partner_names = filter(None,authentication_sheet.col_values(1))[1:]
	num_partners = len(partner_names)

	# Sheet has more rows than partners, so ignore all the blank cells at the end of the column
	decision = authentication_sheet.col_values(columns[access_method])[1:num_partners+1]

	return np.array(partner_names)[np.array(decision) == 'Yes']

def unique_if_partner(partner_shortlist):
	# Return unique periodicals from a shortlist of bundle or proxy periodicals
	return np.unique([i for j, i in enumerate(periodicals) if partners[j] in partner_shortlist])

def collect_data():
	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name('../client_secret.json', scope) # Login to Google
	g_client = gspread.authorize(creds)

	proxy_partners = gen_partner_list('proxy')
	bundle_partners = gen_partner_list('bundle')

	# Pull A-Z list (periodicals and partners) from Wikipedia Library A-Z Sources Search Google Sheet
	az_sheet = get_worksheet('1ndJiMkWvsKpEXZpE5m6bFFgJHulD3M9gDpIIfe-LsKU', 1)

	periodicals = np.array(filter(None,az_sheet.col_values(1)))
	partners = np.array(filter(None,az_sheet.col_values(2)))

	# EBSCO is listed per collection name in A-Z sheet (e.g. EBSCO: MasterFILE Complete)
	# So do a quick search for EBSCO collections and call them all 'EBSCO'
	for l, partner in enumerate(partners):
		if "EBSCO" in partner:
			partners[l] = "EBSCO"

	unique_bundle = unique_if_partner(bundle_partners)
	unique_proxy = unique_if_partner(proxy_partners)
	proxy_no_bundle = len(unique_proxy) - len(unique_bundle)

	num_bundle, num_proxy, num_periodicals = len(unique_bundle), len(unique_proxy), len(np.unique(periodicals))

	proxy_results = {
		'type': 'proxy',
		'periodicals': len(periodicals),
		'unique_periodicals': num_periodicals,
		'proxy': num_proxy,
		'bundle': num_bundle
	}

	return proxy_results