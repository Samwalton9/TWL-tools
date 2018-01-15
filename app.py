# A good portion of this code is based on the Flask tutorial
# (http://flask.pocoo.org/docs/0.12/tutorial/) and flask-login
# tutorial (https://github.com/maxcountryman/flask-login)
#
# Copyright (c) 2017 Wikimedia Foundation, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import flask
import flask_login
import wtforms
import os
from fnmatch import fnmatch
import proxy
import update_pageviews
import metrics
import download_metrics

app = flask.Flask(__name__)
app.config.from_object(__name__)

app.config.from_envvar('TWLTOOLS_SETTINGS', silent=True)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

__dir__ = os.path.dirname(__file__)

loaded_password = open(os.path.join(__dir__,
                                    'config/site_password')).readline().strip()

users = {'admin': {'password': loaded_password}}

app.secret_key = open(os.path.join(__dir__, 'config/secret_key')).readline().strip()


class User(flask_login.UserMixin):
    pass

class PageviewsForm(wtforms.Form):
    form_language = wtforms.StringField(
        'Language', [wtforms.validators.Length(min=2, max=4)])
    form_category = wtforms.StringField('Category')

@login_manager.user_loader
def load_user(username):
    if username not in users:
        return None

    user = User()
    user.id = username
    return user


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username not in users:
        return None

    user = User()
    user.id = username

    return user


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/periodicals', methods=['GET', 'POST'])
@flask_login.login_required
def periodicals():

    if flask.request.method == 'POST':
        if 'submit_proxy' in flask.request.form:
            proxy.collect_proxy_data()
    try:
        results = open('periodicals_data', 'r').readlines()
    except FileNotFoundError:
        results = None

    return flask.render_template('periodicals.html', results=results)


@app.route('/pageviews', methods=['GET', 'POST'])
@flask_login.login_required
def pageviews():
    # Form input for adding languages
    form = PageviewsForm(flask.request.form)
    if flask.request.method == 'POST' and form.validate():
        add_language = update_pageviews.add_new_language(
            form.form_language.data, form.form_category.data)
        flask.flash(add_language)

    # Display pageview logs
    logs_list = list_logs(os.path.join(__dir__, "logs/"), "*.txt")

    if len(logs_list) > 0:
        simple_list = sorted(["_".join(i.split("_")[:3])
                             for i in logs_list
                             if 'latest' not in i
                             and "_run" not in i])
        simple_list.insert(0, 'latest')
    else:
        simple_list = None

    return flask.render_template('pageviews.html',
                                 results=simple_list, type='files', form=form)

@app.route('/pageviews/<log_file>')
@flask_login.login_required
def individual_log(log_file):
    results = open('logs/%s_pageviews_log.txt' % log_file, 'r').readlines()

    return flask.render_template('pageviews.html', results=results, type='log')


@app.route('/metrics', methods=['GET', 'POST'])
def metrics_index():
    if flask.request.method == 'POST':
        download_metrics.download_csv()
        flask.flash('Metrics redownloaded successfully')

    partner_list = metrics.CollectMetrics().list_partners()
    return flask.render_template('metrics.html', partners= partner_list)


@app.route('/metrics/<partner_name>')
def partner_metrics(partner_name):
    pub_metrics = metrics.CollectMetrics(partner_name)
    
    url_metrics, partner_data = pub_metrics.list_urls()
    if url_metrics:
        return flask.render_template('metrics_partner.html',
            partner_data= partner_data, metrics_data= url_metrics)


@app.route('/metrics_info')
def metrics_info():
    return flask.render_template('metrics_info.html')


def open_log(file_name):
    try:
        with open('logs/{}.txt'.format(file_name)) as f:
            log_text = f.readline()
        return log_text
    except FileNotFoundError:
        return


@app.route('/scheduled_tasks')
@flask_login.login_required
def scheduled_tasks():
    metrics_text = open_log('metrics_run')
    pageviews_text = open_log('pageviews_run')

    log_text = {
        'metrics': metrics_text,
        'pageviews': pageviews_text
    }
    return flask.render_template('scheduled_tasks.html', automation_text= log_text)


@app.route('/login', methods=['GET', 'POST'])
def login():

    if flask.request.method == 'POST':
        username = flask.request.form['username']
        if username in users:
            if flask.request.form['password'] == users[username]['password']:
                user = User()
                user.id = username
                flask_login.login_user(user)
                flask.flash('Logged in successfully')
                return flask.redirect(flask.url_for('index'))
            else:
                error_msg = 'Incorrect password'
                return flask.render_template('login.html', error=error_msg)
        else:
            error_msg = 'Incorrect username'
            return flask.render_template('login.html', error=error_msg)

    return flask.render_template('login.html')


@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    flask.flash('Logged out successfully')
    return flask.redirect(flask.url_for('index'))


def list_logs(log_directory, file_pattern):
    final_list = []
    file_list = os.listdir(log_directory)
    for log_file in file_list:
        if fnmatch(log_file, file_pattern):
            final_list.append(log_file)
    return final_list