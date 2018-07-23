import logins
import os

__dir__ = os.path.dirname(__file__)

def download_csv():
	g_client = logins.gspread_login()
	metrics_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM')
	first_metrics_worksheet = metrics_sheet.get_worksheet(0)

	csv_export = first_metrics_worksheet.export()
	metrics_file = os.path.join(__dir__, 'metrics.csv')
	with open(metrics_file, 'wb') as f:
		f.write(csv_export)

	partner_flow_sheet = g_client.open_by_key('18tZJna45CWKpLiCvlzAW0AKxBfIhLRTMKIGvDyeeC6A')
	first_partner_flow_worksheet = partner_flow_sheet.get_worksheet(0)

	csv_export = first_partner_flow_worksheet.export()
	partner_flow_file = metrics_file = os.path.join(__dir__, 'partner_flow.csv')
	with open(partner_flow_file, 'wb') as f:
		f.write(csv_export)

if __name__ == "__main__":
	download_csv()