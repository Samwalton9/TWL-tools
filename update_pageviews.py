# -*- coding: utf-8 -*-
import gspread
import datetime
import mwclient
import os
import glob
from mwviews.api import PageviewsClient
from oauth2client.service_account import ServiceAccountCredentials
from calendar import monthrange

#TODO: Update Global Sums when everything is collected. Maybe.
#TODO: Reschedule if something went wrong
#TODO: Consolidate some code e.g. logging in to a Google Sheet for use between here and metrics/periodicals

__dir__ = os.path.dirname(__file__)

ua = 'Page views collection for The Wikipedia Library. Run by User:Samwalton9'

p = PageviewsClient()

def mwclient_login(language, m_or_p):
	site = mwclient.Site(('https', '%s.wiki%sedia.org' % (current_language, m_or_p)), clients_useragent=ua)
	f = open(os.path.join(__dir__,'api_login.txt'), 'r')
	password = f.readline()[:-1]
	site.login('Samwalton9API', password)

	return site

#Recursively check categories, avoid looping indefinitely.
def listpages(this_site, category_name):
	page_list, category_tracker = [], []
	for page in this_site.Categories[category_name]:
		if page.namespace == 14:
			if page.name not in category_tracker:
				page_list.extend(listpages(this_site,':'.join(page.name.split(":")[1:])))
			else:
				category_tracker.append(page.name)
		if page.namespace in [0, 4, 102]: #Ignore unimportant namespaces
			page_list.append(page.name)
	return page_list


#TODO: Add capability to trigger the addition of a new language from TWL Tools
def add_new_language():
	pass

scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(__dir__, 'client_secret.json'), scope)
g_client = gspread.authorize(creds)

g_sheet = g_client.open_by_key('1hUbMHmjoewO36kkE_LlTsj2JQL9018vEHTeAP7sR5ik')

worksheets = g_sheet.worksheets()
sheets_to_edit = []
for pageview_sheet in worksheets:
	worksheet_title = pageview_sheet.title
	if "pageviews" in worksheet_title and len(worksheet_title) in [12,14]:
		sheets_to_edit.append(worksheet_title)

last_month = datetime.date.today().month - 1
this_year = datetime.date.today().year
if last_month == 12:
	this_year -= 1
days_this_month = monthrange(this_year, last_month)[1]

this_month = {
	'string': '%s/1/%s' %(last_month, this_year),
	'start_date': datetime.date(this_year, last_month, 1),
	'end_date': datetime.date(this_year, last_month, days_this_month),
	'as_datetime': datetime.datetime(this_year, last_month, 1)
}

all_added_pages, languages_skipped, suspicious_data, api_errors = [], [], [], []

for sheet_title in sheets_to_edit:

	worksheet = g_sheet.worksheet(sheet_title)
	global_sums = g_sheet.worksheet('Global Sums')

	current_language = worksheet.title.split(" ")[0].lower()

	if current_language == 'meta':
		p_or_m = 'm'
	else:
		p_or_m = 'p'

	#Find out how many dates we already have, fill the next one
	fill_column = len(list(filter(None,worksheet.row_values(1)))) + 1
	last_column = len(worksheet.row_values(1))

	#Check if we're at the last column, and add one if so
	if fill_column > last_column:
		worksheet.add_cols(1)

	#Check if we've already done this month for some reason
	last_col_date = worksheet.col_values(fill_column-1)[0]
	if last_col_date == this_month['string']:
		same_month = True
		languages_skipped.append("%s (already done)" % current_language)
		print("Skipping", current_language, "(already collected)")
	else:
		print("Collecting", current_language)
		same_month = False

	if same_month == False:
		#See if we need to add pages to this sheet
		current_site = mwclient_login(current_language, p_or_m)
		global_sums_language_list = global_sums.col_values(1)
		lang_idx = global_sums_language_list.index(current_language.lower())
		language_category = global_sums.col_values(3)[lang_idx]
		lang_page_list = listpages(current_site, language_category)

		page_list = list(filter(None,worksheet.col_values(1)[2:]))

		pages_to_add = []
		for page in lang_page_list:
			if page not in page_list:
				pages_to_add.append(page)
				all_added_pages.append('%s - %s' % (current_language, page))

		if len(pages_to_add) > 0:
			for row, record in enumerate(pages_to_add):
				worksheet.update_cell(len(page_list)+3+row, 1, record)

		#Grab this data again, in case we added new pages.
		page_list = list(filter(None,worksheet.col_values(1)[2:]))

		#Initialise our array for the sheet
		#Zero value will be overwritten with sum later
		views_array = [this_month['string'], 0]

		#article_views can take a list, but returns dict, so
		#looping individual pages as a simple way to retain order
		for page_title in page_list:
			try:
				daily_views = p.article_views('%s.wiki%sedia' % (current_language, p_or_m), page_title,
				 								start = this_month['start_date'],
				  								end = this_month['end_date'],
				  								granularity = 'monthly',
				  								agent = 'user')

				this_page_views = daily_views[this_month['as_datetime']][page_title.replace(' ','_')]
			except Exception:
				api_errors.append('Pageviews API error for %s - %s' %(current_language, page_title))
				this_page_views = ''

			#None returned if no pageviews data (not zero pageviews)
			if this_page_views == None:
				this_page_views = ''

			views_array.append(this_page_views)

		#Ignore any '' values when summing
		views_array[1] = sum([i for i in views_array[2:] if not isinstance(i, str)])

		#Update Sheet
		for row, record in enumerate(views_array):
			worksheet.update_cell(row+1, fill_column, record)
			last_value = worksheet.col_values(fill_column-1)[row+1]

#Keep last log, but rename
logs_folder = os.path.join(__dir__,'logs/')

#Make a logs folder if there isn't one yet
folder_exists = os.path.isdir(logs_folder)
if not folder_exists:
	os.mkdir(logs_folder)

log_count = len(glob.glob(logs_folder + '%s_%s_*pageviews_log.txt' % (last_month, this_year)))

try:
	os.rename(logs_folder + 'latest_pageviews_log.txt', logs_folder + '%s_%s_%s_pageviews_log.txt' % (last_month, this_year, log_count+1))
except FileNotFoundError: #Don't worry if there's no file yet
	pass

#Log errors and notes
def log_errors(file, error_array, title_text, subtext=''):
	if len(error_array) > 0:
		f.write('\n%s\n--------------\n%s\n' % (title_text,subtext))
		for error_text in error_array:
			f.write(error_text + "\n")

f = open(logs_folder + 'latest_pageviews_log.txt', 'w')
f.write("Pageviews data collection last ran: %s (UTC)\n" % datetime.datetime.now().strftime("%d %B %Y at %H:%M"))
log_errors(f, all_added_pages, 'New pages')
log_errors(f, languages_skipped, 'Skipped languages')
log_errors(f, api_errors, 'API errors',
			 'Likely the result of a page being deleted or moved.\n')
