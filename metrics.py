import datetime
import gspread
import logins
import pycountry

g_client = logins.gspread_login()
metrics_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM')
first_worksheet = metrics_sheet.get_worksheet(0)

def get_column(worksheet, col_num):
	return list(filter(None,worksheet.col_values(col_num)[1:]))

partner_names = get_column(first_worksheet, 1)
num_partners = len(partner_names)
URL_names = get_column(first_worksheet, 2)
URL_domains = get_column(first_worksheet, 3)
display_check = first_worksheet.col_values(4)[1:num_partners+1]

languages = get_column(first_worksheet, 5)
language_list = [pycountry.languages.get(alpha_2=i) for i in languages]

metrics_dates = first_worksheet.row_values(1)[7:]
all_values = first_worksheet.get_all_values()

def partner_check(partner_name):
	urls_to_show = None
	display_check = list_urls(partner_name)
	if len(display_check) > 0:
		return True
	else:
		return

def list_urls(partner_name):
	selected_urls = []
	for i, URL_domain in enumerate(URL_domains):
		if partner_names[i] == partner_name and display_check[i] == 'x':
			this_partner_metrics = all_values[i][7:]
			this_partner_dates = [metrics_dates[i]
								  for i, x in enumerate(this_partner_metrics)
								  if x != '']
			this_partner_metrics = [int(i.replace(",","")) for i in list(filter(None,this_partner_metrics))]
			
			if max(this_partner_metrics) < 100:
				chart_start = 0
			else:
				chart_start = min(this_partner_metrics) * 0.9

			chart_height = max(this_partner_metrics) + (min(this_partner_metrics) * 0.1)

			selected_urls.append({'URL name': URL_names[i],
								  'Language': language_list[i].name,
								  'Domain': URL_domain,
								  'Link numbers': this_partner_metrics,
								  'Link dates': this_partner_dates,
								  'chart_height': chart_height,
								  'chart_start': chart_start,
								  'Chart name': URL_names[i].replace(" ","")
								 })

	return selected_urls

#print(list_urls('Tilastopaja'))