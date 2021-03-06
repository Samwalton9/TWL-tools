import time
import toolforge
import mwclient
import logins

g_client = logins.gspread_login()
#g_sheet = g_client.open_by_key('1KVuv4BBnmGE_N5a4h0Db55cttwkuCqKD653D7XAYH4I') #Test sheet
g_sheet = g_client.open_by_key('1W7LRnkBrppOx_Yhoa8r0XBMDowGCjmmaHEol7Cj1TvM') #Live sheet
worksheet = g_sheet.get_worksheet(1) # Global numbers

col_numbers = worksheet.col_count

partner_name_list = list(filter(None,worksheet.col_values(1)[1:])) #[1:] for all
url_list = list(filter(None,worksheet.col_values(2)[1:])) #Avoid header, ignore empties

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

protocols = ['http', 'https']

number_of_urls = [date_string] #Date for top of column

sites = ['de', 'en', 'es', 'fr', 'it', 'nl', 'ja', 'pl', 'ru', 'ceb', 'sv', 'vi', 'war']

for i, search_term in enumerate(url_list):
 num_urls = 0
 print(partner_name_list[i], "- %s/%s" %(i+1, len(url_list)))

 if not same_day or (same_day == True and last_data[i+1]) == '': #Ignore any existing data for today

  if "." in search_term: #Only do this for URLs
   search_terms_split = search_term.split(",")
   for sub_url in search_terms_split:
    sub_url = sub_url.strip()  # Catch any trailing spaces
    if sub_url[0] == "*":
     sub_url = sub_url[2:]

    url_start = sub_url.split("/")[0].split(".")[::-1]
    url_optimised = '.'.join(url_start) + ".%"

    if "/" in sub_url:
     url_end = "/".join(sub_url.split("/")[1:])
     url_pattern_end = "%./" + url_end + "%"
    else:
     url_pattern_end = '%'
    
    print("Collecting...")
    print(url_optimised, url_pattern_end)

    for site in sites:
     conn = toolforge.connect('{}wiki'.format(site))
     
     for current_protocol in protocols:
      with conn.cursor() as cur:
       url_pattern_start = current_protocol + "://" + url_optimised

       cur.execute('''SELECT COUNT(*) FROM externallinks
                      WHERE el_index LIKE '%s'
                      AND el_index LIKE '%s'
                      ''' % (url_pattern_start, url_pattern_end))
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
