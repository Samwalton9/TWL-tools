import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

__dir__ = os.path.dirname(__file__)

def gspread_login():
	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name(
	    os.path.join(__dir__, 'config/client_secret.json'), scope)
	g_client = gspread.authorize(creds)
	if creds.access_token_expired:
	    g_client.login()

	return g_client