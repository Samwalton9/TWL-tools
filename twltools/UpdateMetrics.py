import gspread
import time
import mwclient
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
#import pandas as pd - Used for Quarry query if I get around to using that.

scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name('../client_secret.json', scope)
g_client = gspread.authorize(creds)
#g_sheet = g_client.open_by_key('1sVYW4mOAniTq6XKDPSsH-UMrTRzvhPyE7mLQHuzNIi8') #Test sheet
g_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM') #Live sheet
worksheet = g_sheet.get_worksheet(0)

col_numbers = worksheet.col_count

partner_name_list = filter(None,worksheet.col_values(1)[1:]) #[1:] for all
url_list = filter(None,worksheet.col_values(2)[1:]) #Avoid header, ignore empties
language_list = filter(None, worksheet.col_values(3)[1:])

last_col_date = worksheet.col_values(col_numbers)[0]

date_string = time.strftime("%-m/%-d/%Y")

if last_col_date == date_string:
 same_day = True
else:
 same_day = False

if same_day == True:
 previous_data = worksheet.col_values(col_numbers-1) #Get the last day, not the one we're working on.
 last_data = worksheet.col_values(col_numbers)
else:
 previous_data = worksheet.col_values(col_numbers)

ua = 'Wikipedia Library Metrics Updater run by User:Samwalton9'

protocols = ['http', 'https']

number_of_urls = [date_string] #Date for top of column
signed_in = False
current_site = None

#Need to allow new URLs to be collected.

for i, search_term in enumerate(url_list):
 num_urls = 0
 print partner_name_list[i], "- %s/%s" %(i+1, len(url_list))
 if not same_day or (same_day == True and last_data[i+1]) == '': #If we're finishing the current day, ignore existing data

  if int(previous_data[i+1]) < 20000 and "." in search_term: #Only do this if it will be time efficient and a URL
   if not signed_in or current_site != language_list[i].strip(): #Do blocks of the same language without signing in each time.
    print "New language, signing in. (%s => %s)" %(current_site, language_list[i].strip())
    site = mwclient.Site(('https', '%s.wikipedia.org' %language_list[i].strip()), clients_useragent=ua) #Need to force HTTPS for some reason

    site.login('Samwalton9API', 'samisapitesting')
    signed_in = True
    current_site = site.host[1][0:2]
 	 
   print "Collecting..."
   for current_protocol in protocols:
    exturls = site.exturlusage(search_term.strip(), protocol=current_protocol)
    this_num_urls = sum([1 for _ in exturls])
    num_urls += this_num_urls
    print current_protocol, this_num_urls

  else:
   print "Too many links."
   num_urls = ""

  number_of_urls.append(num_urls)
  
  print num_urls
 else:
  number_of_urls.append(last_data[i+1])
  print 'Already recorded.'

if same_day == False:
 worksheet.add_cols(1) #Add a new column for today
 col_numbers += 1

print number_of_urls

for row, record in enumerate(number_of_urls):
 if same_day == True and last_data[row] != record: #If we're doing the same day only update new records
  worksheet.update_cell(row+1, col_numbers, record)
 if same_day == False:
  worksheet.update_cell(row+1, col_numbers, record)