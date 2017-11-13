import gspread
from oauth2client.service_account import ServiceAccountCredentials

def gspread_login():
	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name(
	    'client_secret.json', scope)
	g_client = gspread.authorize(creds)
	if creds.access_token_expired:
	    g_client.login()

	return g_client