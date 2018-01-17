TWL Tools
===============

This is a simple interface for accessing a handful of Python scripts and tools on the [Wikipedia Library team](https://meta.wikimedia.org/wiki/The_Wikipedia_Library).

Local install instructions
===============

To install the tool locally, first set up Git and clone the repository to your PC.

You can install the necessary dependencies for the project with `pip install -r requirements.txt`

There are four secret files you will need, placed in the 'config' folder:

* *api_login.txt*: This file should contain a username and password, one line each, for logging in to the MediaWiki API. You may want to create an account specifically for this purpose for security reasons.
* *client_secret.json*: This file is used for logging in to Google Sheets. Follow [Step 1 in this guide](https://developers.google.com/sheets/api/quickstart/python) to generate one. A member of the TWL team will need to add your `client_email` to the relevant docs before you can log in.
* *secret_key*: You can generate one with `os.urandom(24)` in Python.
* *site_password*: This file contains the password needed to log in to the site. Yes, it's plain text. Yes, we should *probably* change that. I'm not too concerned right now because there's no private data on the site; the password just protects some API calls and forms that I'd rather people didn't press if they don't need to. This can be set to anything you like for a local install.

You can start the app with:
```
export FLASK_APP=app
flask run
```

from the top level directory.

Toolforge
===============

TWL Tools runs as *twltools* on Toolforge, accessible at https://tools.wmflabs.org/twltools/.

Maintainers of the tool (https://toolsadmin.wikimedia.org/tools/id/twltools) can connect to Toolforge (`ssh -i ~/.ssh/id_rsa [username]@login.tools.wmflabs.org`) and `become twltools` to access TWL Tools files. The contents of this repo are located in `www/python/src/`

The virtual environment and webservice components of the tool were setup following this guide: https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Flask_OAuth_tool

To interact with the webservice use the following commands:

* Start: `webservice --backend=kubernetes python start`
* Stop: `webservice stop`
* Restart: `webservice restart`

To view a list of scheduled tasks, type `crontab -l`. Current scheduled tasks should be pageview metrics collection on the 3rd of each month, metrics collection once per week, and a daily download of the Metrics and Partner Flow Google Sheets as CSV files. You can type `crontab -e` to edit these tasks. See http://www.adminschoice.com/crontab-quick-reference for instructions.
