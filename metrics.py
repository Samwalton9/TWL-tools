import datetime
import gspread
import logins
import pycountry
import re

def get_column(worksheet, col_num):
	return list(filter(None,worksheet.col_values(col_num)[1:]))

class CollectMetrics:

	def __init__(self, partner_name):
		self.partner_name = partner_name
		g_client = logins.gspread_login()
		metrics_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM')
		first_worksheet = metrics_sheet.get_worksheet(0)


		self.partner_names = get_column(first_worksheet, 1)
		num_partners = len(self.partner_names)
		self.URL_names = get_column(first_worksheet, 2)
		self.URL_domains = get_column(first_worksheet, 3)
		self.display_check = first_worksheet.col_values(4)[1:num_partners+1]

		languages = get_column(first_worksheet, 5)
		self.language_list = [pycountry.languages.get(alpha_2=i) for i in languages]

		self.metrics_dates = first_worksheet.row_values(1)[7:]
		self.all_values = first_worksheet.get_all_values()

	def list_urls(self):
		selected_urls = []
		for i, URL_domain in enumerate(self.URL_domains):
			if self.partner_names[i] == self.partner_name and self.display_check[i] == 'x':
				this_partner_metrics = self.all_values[i+1][7:]
				this_partner_dates = [self.metrics_dates[i]
									  for i, x in enumerate(this_partner_metrics)
									  if x != '']
				this_partner_metrics = [int(i.replace(",","")) for i in list(filter(None,this_partner_metrics))]

				if max(this_partner_metrics) < 100:
					chart_start = 0
				else:
					chart_start = min(this_partner_metrics) * 0.9

				chart_height = max(this_partner_metrics) + (min(this_partner_metrics) * 0.1)

				selected_urls.append({'URL name': self.URL_names[i],
									  'Language': self.language_list[i].name,
									  'Domain': URL_domain,
									  'Link numbers': this_partner_metrics,
									  'Link dates': this_partner_dates,
									  'chart_height': chart_height,
									  'chart_start': chart_start,
									  'Chart name': re.sub('\W+','',self.URL_names[i])
									 })
		if len(selected_urls) > 0:
			return selected_urls
		else:
			return

