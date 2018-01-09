import datetime
import pycountry
import pandas as pd
import download_metrics

class CollectMetrics:

	def __init__(self, partner_name= None):
		self.partner_name = partner_name
		try:
			self.metrics_data = pd.read_csv('metrics.csv')
		except FileNotFoundError:
			download_metrics.download_csv()
			self.metrics_data = pd.read_csv('metrics.csv')

		partner_data = self.metrics_data['Partner']
		self.partner_names = partner_data[pd.notna(partner_data)].tolist()
		num_partners = len(self.partner_names)
		self.URL_names = self.metrics_data['URL'].tolist()
		self.URL_domains = self.metrics_data['Domain'].tolist()
		self.display_check = self.metrics_data['Display?'].tolist()[0:num_partners+1]
		self.notes = self.metrics_data['Notes'].tolist()

		languages = self.metrics_data['Language'].tolist()
		self.language_list = [pycountry.languages.get(alpha_2=i) for i in languages]

		self.metrics_dates = self.metrics_data.columns.tolist()[7:]

	def list_partners(self):
		partner_list = [x for i,x in enumerate(self.partner_names) if self.display_check[i] == 'x']
		return sorted(set(partner_list))

	def list_urls(self):
		selected_urls = []
		for i, URL_domain in enumerate(self.URL_domains):
			if self.partner_names[i] == self.partner_name and self.display_check[i] == 'x':
				this_partner_metrics = self.metrics_data.iloc[i,7:].tolist()
				this_partner_dates = [self.metrics_dates[i]
									  for i, x in enumerate(this_partner_metrics)
									  if pd.notna(x)]
				this_partner_metrics = [int(float(str(i).replace(",",""))) for i in this_partner_metrics if pd.notna(i)]

				if "," in URL_domain:
					domain_split = URL_domain.split(",")
					domain_string = "{} and {}".format(domain_split[0],domain_split[1])
				else:
					domain_string = URL_domain

				max_links = max(this_partner_metrics)
				min_links = min(this_partner_metrics)

				if max_links < 100:
					chart_start = 0
				else:
					chart_start = min_links * 0.9

				if max_links > 15:
					chart_height = round(max_links + ((max_links - min_links) * 0.1))
				else:
					chart_height = 15

				dates_iso = ["%s-%s-%s" %(date.split("/")[2], date.split("/")[0], date.split("/")[1]) for date in this_partner_dates]
				this_partner_note = None
				if pd.notna(self.notes[i]):
					this_partner_note = self.notes[i]

				selected_urls.append({'URL name': self.URL_names[i],
									  'Language': self.language_list[i].name,
									  'Domain': domain_string,
									  'Link numbers': this_partner_metrics,
									  'Link dates': dates_iso,
									  'chart_height': chart_height,
									  'chart_start': round(chart_start,-1),
									  'notes': this_partner_note
									 })
		if len(selected_urls) > 0:
			return selected_urls
		else:
			return
