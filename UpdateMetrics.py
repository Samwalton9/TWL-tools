import gspread
import time
import toolforge
import mwclient
import numpy as np
import logins

g_client = logins.gspread_login()
g_sheet = g_client.open_by_key('1KVuv4BBnmGE_N5a4h0Db55cttwkuCqKD653D7XAYH4I') #Test sheet
#g_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM') #Live sheet
worksheet = g_sheet.get_worksheet(0)

col_numbers = worksheet.col_count

partner_name_list = list(filter(None,worksheet.col_values(1)[1:])) #[1:] for all
url_list = list(filter(None,worksheet.col_values(2)[1:])) #Avoid header, ignore empties
language_list = list(filter(None, worksheet.col_values(3)[1:]))

last_col_date = worksheet.col_values(col_numbers)[0]

date_string = time.strftime("%-m/%-d/%Y")

if last_col_date == date_string:
 same_day = True
else:
 same_day = False

if same_day:
 previous_data = worksheet.col_values(col_numbers-1) #Get the last day, not the one we're working on.
 last_data = worksheet.col_values(col_numbers)
else:
 previous_data = worksheet.col_values(col_numbers)

ua = 'Wikipedia Library Metrics Updater run by User:Samwalton9'

protocols = ['http', 'https']

number_of_urls = [date_string] #Date for top of column
connected = False
current_site = None

for i, search_term in enumerate(url_list):
 num_urls = 0
 url_language = language_list[i].strip()
 print(partner_name_list[i], "- %s/%s" %(i+1, len(url_list)))

 if not same_day or (same_day == True and last_data[i+1]) == '': #Ignore any existing data for today

  if "." in search_term: #Only do this for URLs
   if not connected or current_site != url_language: #Do blocks of the same language without making new database connections.
    print("New language, reconnecting to DB. (%s => %s)" %(current_site, url_language))
    conn = toolforge.connect('{}wiki'.format(url_language))
    current_site = url_language
    connected = True

   if search_term[0] == "*":
    search_term = search_term[2:]  # Remove *.

   url_start = search_term.split("/")[0].split(".")[::-1]
   url_optimised = '.'.join(url_start) + "%"

   if "/" in search_term:
    url_end = search_term.split("/")[1:]
    url_optimised += "/" + '/'.join(url_end) + "%"
 	 
   print("Collecting...")
   for current_protocol in protocols:
    with conn.cursor() as cur:
     url_pattern = current_protocol + "://" + url_optimised
     print(url_pattern)

     cur.execute('''SELECT COUNT(*) FROM page, externallinks
                    WHERE page_id = el_from
                    AND el_index LIKE '%s'
                    ''' % url_pattern)
     this_num_urls = cur.fetchone()[0]

    num_urls += this_num_urls
    print(this_num_urls)

  else:
   # TODO: Do a mwclient search for text queries - DB doesn't contain full text
   # print "Too many links."
   num_urls = ""

  number_of_urls.append(num_urls)
  
 else:
  number_of_urls.append(last_data[i+1])
  print('Already recorded.')

if same_day == False:
 worksheet.add_cols(1) #Add a new column for today
 col_numbers += 1

for row, record in enumerate(number_of_urls):
 if same_day == True and last_data[row] != record: #If we're doing the same day only update new records
  worksheet.update_cell(row+1, col_numbers, record)
 if same_day == False:
  worksheet.update_cell(row+1, col_numbers, record)