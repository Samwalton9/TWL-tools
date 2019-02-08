import datetime
import pycountry
import pandas as pd
import download_metrics

# TODO: Add more relevant information from partner flow e.g. start date
# TODO: Make better use of pandas than converting everything to lists

def open_csv(file_name):
	try:
		return pd.read_csv(file_name)
	except FileNotFoundError:
		download_metrics.download_csv()
		return pd.read_csv(file_name)

class CollectMetrics:

	def __init__(self, partner_name= None):
		self.partner_name = partner_name
		self.metrics_data = open_csv('metrics.csv')
		self.partner_flow = open_csv('partner_flow.csv')

		partner_data = self.metrics_data['Partner']
		self.partner_names = partner_data[pd.notna(partner_data)].tolist()
		num_partners = len(self.partner_names)
		self.URL_names = self.metrics_data['URL'].tolist()
		self.URL_domains = self.metrics_data['Domain'].tolist()
		self.display_check = self.metrics_data['Display?'].tolist()[0:num_partners+1]
		self.notes = self.metrics_data['Notes'].tolist()

		self.languages = self.metrics_data['Language'].tolist()
		self.language_list = [pycountry.languages.get(alpha_2=i) for i in self.languages]

		self.metrics_dates = self.metrics_data.columns.tolist()[7:]

		partner_flow_partners = self.partner_flow['Partner'].tolist()
		library_card = self.partner_flow['Library card platform'].tolist()
		if partner_name:
			self.library_card_link = library_card[partner_flow_partners.index(partner_name)]
			if pd.isna(self.library_card_link):
				self.library_card_link = None


	def list_partners(self):
		partner_list = [x for i,x in enumerate(self.partner_names) if self.display_check[i] == 'x']
		return sorted(set(partner_list))

	def list_urls(self):
		selected_urls = []
		for i, URL_domain in enumerate(self.URL_domains):
			if self.partner_names[i] == self.partner_name and self.display_check[i] == 'x':
				this_partner_metrics = self.metrics_data.iloc[i,7:].tolist()
				this_partner_dates = [self.metrics_dates[j]
									  for j, x in enumerate(this_partner_metrics)
									  if pd.notna(x)]
				this_partner_metrics = [int(float(str(k).replace(",",""))) for k in this_partner_metrics if pd.notna(k)]

				domain_split = URL_domain.split(",")
				domain_string = " and ".join(domain_split)

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

				url_structure = "https://{}.wikipedia.org/w/index.php?title=Special:LinkSearch&limit=5000&offset=0&target={}://{}"

				LinkSearch_URLs = {}
				for this_url_domain in domain_split:
					LinkSearch_URLs[this_url_domain] = {'HTTP': url_structure.format(self.languages[i], 'http', this_url_domain),
									   					'HTTPS': url_structure.format(self.languages[i], 'https', this_url_domain)
									  				   }

				selected_urls.append({'URL name': self.URL_names[i],
									  'Language': self.language_list[i].name,
									  'Domain': domain_string,
									  'Link numbers': this_partner_metrics,
									  'Link dates': dates_iso,
									  'chart_height': chart_height,
									  'chart_start': round(chart_start,-1),
									  'notes': this_partner_note,
									  'linksearch_urls': LinkSearch_URLs
									 })
		partner_data = {'Partner name': self.partner_name,
				        'Library card': self.library_card_link
					   }
		if len(selected_urls) > 0:
			return selected_urls, partner_data
		else:
			return
