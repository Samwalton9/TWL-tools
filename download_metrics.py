import logins

def download_csv():
	g_client = logins.gspread_login()
	metrics_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM')
	first_worksheet = metrics_sheet.get_worksheet(0)

	csv_export = first_worksheet.export()
	with open('metrics.csv', 'wb') as f:
		f.write(csv_export)

if __name__ == "__main__":
	download_csv()