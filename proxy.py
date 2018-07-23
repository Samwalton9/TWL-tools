import datetime
import numpy as np
import gspread
import logins

def get_worksheet(key, sheet_num):
    # Return a worksheet given a sheet key and tab number
    g_client = logins.gspread_login()
    g_sheet = g_client.open_by_key(key)
    worksheet = g_sheet.get_worksheet(sheet_num)

    return worksheet

def gen_partner_list(access_method):
    # Returns a list of partners that said 'Yes' to proxy or bundle
    columns = {'proxy': 8, 'bundle': 9}

    authentication_sheet = get_worksheet(
        '1BCldgV2ny6YOlubciOB2dzhGlKJiWgNQVa3FLTG0180', 0)
    partner_names = list(filter(None,
                                authentication_sheet.col_values(1)))[1:]
    num_partners = len(partner_names)

    # Sheet has more rows than partners
    # so ignore all the cells at the end of the column
    decision = authentication_sheet.col_values(columns[access_method])
    decision = decision[1:num_partners+1]

    return np.array(partner_names)[np.array(decision) == 'Yes']

def unique_if_partner(partners, periodicals, partner_shortlist):
    # Return unique periodicals from a shortlist of partners
    return np.unique([i for j, i in enumerate(periodicals)
                     if partners[j] in partner_shortlist])

# Pull A-Z list (periodicals and partners) from
# Wikipedia Library A-Z Sources Search Google Sheet
def get_data():
    az_sheet = get_worksheet(
        '1ndJiMkWvsKpEXZpE5m6bFFgJHulD3M9gDpIIfe-LsKU', 1)

    periodicals = np.array(list(filter(None, az_sheet.col_values(1))))
    partners = np.array(list(filter(None, az_sheet.col_values(2))))

    # EBSCO is listed differently for each collection
    # So do a quick search for EBSCO collections and name them all 'EBSCO'
    for l, partner in enumerate(partners):
        if "EBSCO" in partner:
            partners[l] = "EBSCO"

    return partners, periodicals

def collect_proxy_data():

    proxy_partners = gen_partner_list('proxy')
    bundle_partners = gen_partner_list('bundle')

    current_partners, current_periodicals = get_data()

    unique_bundle = unique_if_partner(
        current_partners, current_periodicals, bundle_partners)
    unique_proxy = unique_if_partner(
        current_partners, current_periodicals, proxy_partners)
    proxy_no_bundle = len(unique_proxy) - len(unique_bundle)

    num_bundle = len(unique_bundle)
    num_proxy = len(unique_proxy)
    num_periodicals = len(np.unique(current_periodicals))
    fraction_proxy = 100 * (num_proxy/num_periodicals)
    fraction_bundle = 100 * (num_bundle/num_periodicals)

    date_string = datetime.datetime.now().strftime("%d %B %Y at %H:%M")
    data_output = ["Data generated: %s (UTC)" % date_string,
                   "",
                   "Total periodicals: %s" % len(current_periodicals),
                   "Unique periodicals: %s" % num_periodicals,
                   "Periodicals accessible by proxy: %s (%.1f%%)" % (
                    num_proxy, fraction_proxy),
                   "Bundle periodicals: %s (%.1f%%)" % (
                    num_bundle, fraction_bundle)]

    with open('periodicals_data', 'w') as f:
        for line in data_output:
            f.write(line + "\n")