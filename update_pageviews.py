# -*- coding: utf-8 -*-
import gspread
import datetime
import time
import mwclient
import os
import glob
import pycountry
from mwviews.api import PageviewsClient
from calendar import monthrange
import logins

# TODO: Reschedule if something went wrong
# TODO: Investigate and fix SSLError when trying to do
#       gpsread stuff while pageviews is collecting

__dir__ = os.path.dirname(__file__)

ua = 'Page views collection for The Wikipedia Library. Run by User:Samwalton9'
p = PageviewsClient()

g_client = logins.gspread_login()
# Test sheet - 17Vr9o9ytiv-5l9g3TdUoheEJldWKFxZrUTiIJQI-Ucg
# Live sheet - 1hUbMHmjoewO36kkE_LlTsj2JQL9018vEHTeAP7sR5ik
# Pageviews sheet
g_sheet = g_client.open_by_key('17Vr9o9ytiv-5l9g3TdUoheEJldWKFxZrUTiIJQI-Ucg')
global_sums = g_sheet.worksheet('Global Sums')


def mwclient_login(language):

    if language == 'meta':
        p_m = 'm'
    else:
        p_m = 'p'

    site = mwclient.Site(('https', '%s.wiki%sedia.org' % (language, p_m)),
                         clients_useragent=ua)
    with open(os.path.join(__dir__, 'api_login.txt'), 'r') as f:
        username = f.readline().strip()
        password = f.readline().strip()
        site.login(username, password)

    return site


# Recursively check categories, avoid looping indefinitely.
def listpages(this_site, category_name):
    page_list, category_tracker = [], []
    for page in this_site.Categories[category_name]:
        if page.namespace == 14:
            if page.name not in category_tracker:
                cat_pages = listpages(this_site,
                                      ':'.join(page.name.split(":")[1:]))
                page_list.extend(cat_pages)
            else:
                category_tracker.append(page.name)
        if page.namespace in [0, 4, 102]:  # Ignore unimportant namespaces
            page_list.append(page.name)
    return page_list


def add_new_language(input_language, category_name):
    input_language = input_language.lower()

    worksheet_title = input_language.upper() + ' pageviews'
    language = pycountry.languages.get(alpha_2=input_language)

    worksheet_exists = True
    try:
        g_sheet.worksheet(worksheet_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet_exists = False

    if worksheet_exists:
        return "A sheet for this language already exists."
    else:
        site = mwclient_login(input_language)
        category_exists = site.Categories[category_name].exists
        if category_exists:
            g_sheet.add_worksheet(worksheet_title, 1000, 50)

            worksheet = g_sheet.worksheet(worksheet_title)
            heading_text = ('Category members for '
                            '%s Wikipedia Library' % language.name)
            worksheet.update_cell(1, 1, heading_text)

            # Just grab dates from another sheet we know exists
            default_dates = list(filter(None, g_sheet.worksheet(
                'EN pageviews').row_values(1)[1:]))
            for i, date in enumerate(default_dates):
                worksheet.update_cell(1, i+2, date)

            offset = 4
            languages = global_sums.col_values(1)[offset:]
            lang_idx = languages.index('meta')  # Should be the last one
            new_row = lang_idx + offset + 1
            language_category = global_sums.insert_row('',index=new_row)
            global_sums.update_cell(new_row, 1, input_language)
            global_sums.update_cell(new_row, 3, category_name)

            return "New language added!"
        else:
            return "Category is empty or doesn't exist."

    return None


# Log errors and notes
def log_errors(file, error_array, title_text, subtext=''):
    if len(error_array) > 0:
        file.write('\n%s\n--------------\n%s\n' % (title_text, subtext))
        for error_text in error_array:
            file.write(error_text + "\n")


def month_dict(month, year, col):

    days_in_month = monthrange(year, month)[1]

    return {
        'string': '%s/1/%s' % (month, year),
        'start_date': datetime.date(year, month, 1),
        'end_date': datetime.date(year, month, days_in_month),
        'as_datetime': datetime.datetime(year, month, 1),
        'column_number': col
    }


def collect_views(site_name, page_name, month):
    try:
        daily_views = p.article_views(site_name, page_name,
                                      start=month['start_date'],
                                      end=month['end_date'],
                                      granularity='monthly',
                                      agent='user')

        formatted_page_name = page_name.replace(' ', '_')
        this_page_views = daily_views[month['as_datetime']][formatted_page_name]
    except Exception as e:
        this_page_views = ''

    # None returned if no pageviews data (not zero pageviews)
    if this_page_views is None:
        this_page_views = ''

    return this_page_views


def update_pageviews():

    worksheets = g_sheet.worksheets()
    sheets_to_edit = []
    for pageview_sheet in worksheets:
        worksheet_title = pageview_sheet.title
        if ("pageviews" in worksheet_title and
                len(worksheet_title) in [12, 13, 14]):
            sheets_to_edit.append(worksheet_title)

    last_month = datetime.date.today().month - 1
    this_year = datetime.date.today().year
    if last_month == 12:
        this_year -= 1
    days_this_month = monthrange(this_year, last_month)[1]

    all_added_pages, languages_skipped = [], []

    for sheet_title in sheets_to_edit:

        worksheet = g_sheet.worksheet(sheet_title)

        date_row = g_sheet.worksheet(sheet_title).row_values(1)[1:]
        sheet_dates = list(filter(None, date_row))
        full_months = []
        for col, column_date in enumerate(sheet_dates):
            date_split = column_date.split('/')
            col_month = int(date_split[0])
            col_year = int(date_split[-1])
            full_months.append(month_dict(col_month, col_year, col+2))
        this_month = month_dict(last_month, this_year, len(sheet_dates)+2)
        full_months.append(this_month)

        current_language = worksheet.title.split(" ")[0].lower()

        # Check if we've already done this month for some reason
        last_col_date = worksheet.col_values(this_month['column_number']-1)[0]
        if last_col_date == this_month['string']:
            same_month = True
            languages_skipped.append("%s (already done)" % current_language)
            print("Skipping", current_language, "(already collected)")
        else:
            print("Collecting", current_language)
            same_month = False

        if not same_month:
            # Check if we're at the last column, and add one if so
            if this_month['column_number'] > worksheet.col_count:
                worksheet.add_cols(1)

            worksheet.update_cell(1, this_month['column_number'],
                                  this_month['string'])

            # See if we need to add pages to this sheet
            current_site = mwclient_login(current_language)
            global_sums_language_list = global_sums.col_values(1)
            lower_lang = current_language.lower()
            lang_idx = global_sums_language_list.index(lower_lang)
            language_category = global_sums.col_values(3)[lang_idx]
            lang_page_list = listpages(current_site, language_category)

            page_list = list(filter(None, worksheet.col_values(1)[1:]))
            previous_pages = len(page_list)

            pages_to_add = []
            for page in lang_page_list:
                if page not in page_list:
                    pages_to_add.append(page)
                    page_list.append(page)
                    all_added_pages.append('%s - %s' % (current_language, page))

            if len(pages_to_add) > 0:
                num_rows = worksheet.row_count
                for row, record in enumerate(pages_to_add):
                    update_row = previous_pages+2+row
                    if update_row > num_rows:
                        worksheet.add_rows(10)
                    worksheet.update_cell(update_row, 1, record)
                sheet_months = full_months
            else:
                sheet_months = [this_month]

            # Add pageviews only if we're collecting for the latest month
            # or if the page is new for a previous month
            for i, month in enumerate(sheet_months):
                if len(sheet_months) == 1:
                    upd_col = this_month['column_number']
                else:
                    upd_col = i+2
                for j, page_title in enumerate(page_list):
                    # Try to keep Docs logged in.
                    g_client.login()
                    if month['string'] == this_month['string'] or page_title in pages_to_add:
                        page_views = collect_views(current_site.host[1][:-4],
                                                   page_title,
                                                   month)
                        try:
                            try:
                                worksheet.update_cell(j+2, upd_col, page_views)
                            # A gspread bug causes a TypeError to be raised
                            # in the process of returning a RequestError
                            # while asking to wait 30s and try again.
                            # Rarely, but sometimes, errors twice.
                            except gspread.exceptions.RequestError as e:
                                g_client.login()
                                pass
                        except TypeError:
                            time.sleep(30)
                            worksheet.update_cell(j+2, upd_col, page_views)

    # Update Global Sums
    # TODO: Update total pages automatically
    # TODO: Only back-date summing if we added new pages for a language/date
    print("Updating global sums sheet")
    g_sums_languages = global_sums.col_values(1)[4:4+len(sheets_to_edit)]
    g_dates = list(filter(None, global_sums.row_values(1)[4:]))
    if g_dates[-1] != this_month['string']:
        global_sums.add_cols(1)
        g_dates.append(this_month['string'])
    for ii, lang in enumerate(g_sums_languages):
        print(lang)
        g_worksheet = g_sheet.worksheet('%s pageviews' % lang.upper())
        for jj, g_month in enumerate(g_dates):
            g_row = ii + 5
            g_col = jj + 5
            pageview_values = list(filter(None, g_worksheet.col_values(g_col-3)[1:]))
            cell_sum = sum([int(i) for i in pageview_values])
            global_sums.update_cell(g_row, g_col, cell_sum)

    # Code would be more efficient if we reversed the above two for loops
    # But outweighed by the extra API calls necessary, so requires us to loop again here
    for jj, g_month in enumerate(g_dates):
        this_col = list(filter(None, global_sums.col_values(jj+5)[4:]))
        total, global_total = 0, 0
        for ii, lang in enumerate(g_sums_languages):
            if lang != 'en':
                global_total += int(this_col[ii])
            total += int(this_col[ii])
        fraction = 100*(global_total/float(total))
        global_sums.update_cell(2, jj+5, total)
        global_sums.update_cell(3, jj+5, global_total)
        global_sums.update_cell(4, jj+5, '%.1f%%' % fraction)


    # Keep last log, but rename
    logs_folder = os.path.join(__dir__, 'logs/')

    # Make a logs folder if there isn't one yet
    folder_exists = os.path.isdir(logs_folder)
    if not folder_exists:
        os.mkdir(logs_folder)

    log_count = len(glob.glob(logs_folder + '%s_%s_*pageviews_log.txt' % (last_month, this_year)))

    try:
        os.rename(logs_folder + 'latest_pageviews_log.txt',
                  logs_folder + '%s_%s_%s_pageviews_log.txt' % (last_month, this_year, log_count+1))
    except FileNotFoundError:  # Don't worry if there's no file yet
        pass

    with open(logs_folder + 'latest_pageviews_log.txt', 'w') as f:
        f.write("Pageviews data collection run: %s (UTC)\n" % datetime.datetime.now().strftime("%d %B %Y at %H:%M"))
        log_errors(f, all_added_pages, 'New pages')
        log_errors(f, languages_skipped, 'Skipped languages')

if __name__ == '__main__':
    update_pageviews()
