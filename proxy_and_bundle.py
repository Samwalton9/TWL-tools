import gspread
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name('../client_secret.json', scope) # Login to Google
g_client = gspread.authorize(creds)

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

# Print everything to the terminal
print "Total periodicals:", len(periodicals)
print "Number of unique periodicals:", num_periodicals
print "Number of periodicals accessible by proxy:", len(unique_proxy), "(%.1f%%)" %(100*float(num_proxy)/num_periodicals)
print "Number of periodicals accessible by proxy but not bundle:", proxy_no_bundle
print "Number of bundle periodicals:", len(unique_bundle), "(%.1f%%)" %(100*float(num_bundle)/num_periodicals)