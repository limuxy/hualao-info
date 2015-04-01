# -*- coding: utf-8 -*-
from flask import Flask, session, redirect, url_for, render_template, request, g
from rauth import OAuth1Service
from functools import wraps
from dateutil import parser
from dateutil.relativedelta import *
import time, sqlite3
app = Flask(__name__)
app.debug = True
app.secret_key = ''
app.database = "hualao.db"


def connect_db():
    return sqlite3.connect(app.database)

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

fanfou = OAuth1Service(
        name='fanfou',
        consumer_key='3f8fec3e2d09c65bebd78f202bee08b3',
        consumer_secret='2139688a9427f8dd1d4605c88fcefe58',
        request_token_url='http://fanfou.com/oauth/request_token',
        access_token_url='http://fanfou.com/oauth/access_token',
        authorize_url='http://fanfou.com/oauth/authorize',
        base_url='http://api.fanfou.com/')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session['logged_in'] != True:
            return redirect(url_for(('login')))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login():
    session['request_token'], session['request_token_secret'] = fanfou.get_request_token()
    authorize_url = fanfou.get_authorize_url(session['request_token'])
    callback_url = url_for('authorized', _external=True)
    authorize_url = authorize_url+"&oauth_callback="+callback_url
    return render_template('login.html', authorize_url=authorize_url)

@app.route('/authorized', methods=['GET'])
def authorized():
    session['oauth_token'] = request.args.get('oauth_token')
    handler = fanfou.get_auth_session(session['request_token'], session['request_token_secret'])
    resp = handler.get('account/verify_credentials.json')
    user_info = resp.json()
    session['user_id'] = user_info['id']
    session['username'] = user_info['name']
    session['access_token'] = handler.access_token
    session['access_token_secret'] = handler.access_token_secret
    session['logged_in'] = True
    return redirect(url_for('index'))

@app.route('/')
@login_required
def index():
    current_date = time.strftime("%Y-%m-%d")
    cur = g.db.execute('select id, time, content, photo_url from diary where user_id=? and date=? order by time',(session['user_id'], current_date))
    statuses = cur.fetchall()
    return render_template('index.html', statuses=statuses)

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

@app.route('/action/morning')
@login_required
def act_morning():
    handler = fanfou.get_session((session['access_token'], session['access_token_secret']))
    status = u"起床啦！早安！"
    data = {'status': status,}
    r = handler.post('statuses/update.json', data=data)
    result = r.json()
    fanfou_id = result['id']
    current_date = time.strftime("%Y-%m-%d")
    current_time = time.strftime("%H:%M")
    user_id = session['user_id']
    g.db.execute("insert into diary (user_id, date, time, content, fanfou_id) values (?, ?, ?, ?, ?)", (user_id, current_date, current_time, status, fanfou_id))
    g.db.commit()
    return redirect(url_for('index'))

@app.route('/action/sleep')
@login_required
def act_sleep():
    handler = fanfou.get_session((session['access_token'], session['access_token_secret']))
    status = u"睡觉啦！晚安！"
    data = {'status': status,}
    r = handler.post('statuses/update.json', data=data)
    result = r.json()
    fanfou_id = result['id']
    current_date = time.strftime("%Y-%m-%d")
    current_time = time.strftime("%H:%M")
    user_id = session['user_id']
    g.db.execute("insert into diary (user_id, date, time, content, fanfou_id) values (?, ?, ?, ?, ?)", (user_id, current_date, current_time, status, fanfou_id))
    g.db.commit()
    return redirect(url_for('index'))

@app.route('/action/food', methods=['GET', 'POST'])
@login_required
def act_food():
    if request.method == 'GET':
        return render_template('act_food.html')
    else:
        fan_time = request.form['time']
        food = request.form['food']
        memo = request.form['memo']
        if fan_time == None or fan_time =="":
            status = u"吃了: " + food + " "+ memo
        else:
            status = fan_time + ": " + food + " " + memo
        handler = fanfou.get_session((session['access_token'], session['access_token_secret']))
        data = {'status':status,}
        r = handler.post('statuses/update.json', data=data)
        result = r.json()
        fanfou_id = result['id']
        current_date = time.strftime("%Y-%m-%d")
        current_time = time.strftime("%H:%M")
        user_id = session['user_id']
        g.db.execute("insert into diary (user_id, date, time, content, fanfou_id) values (?, ?, ?, ?, ?)", (user_id, current_date, current_time, status, fanfou_id))
        g.db.commit()
        return redirect(url_for('index'))

@app.route('/action/say', methods=['POST'])
@login_required
def act_say():
    if request.method == 'POST':
        status = request.form['status']
        handler = fanfou.get_session((session['access_token'], session['access_token_secret']))
        data = {'status':status,}
        r = handler.post('statuses/update.json', data=data)
        result = r.json()
        fanfou_id = result['id']
        current_date = time.strftime("%Y-%m-%d")
        current_time = time.strftime("%H:%M")
        user_id = session['user_id']
        g.db.execute("insert into diary (user_id, date, time, content, fanfou_id) values (?, ?, ?, ?, ?)", (user_id, current_date, current_time, status, fanfou_id))
        g.db.commit()
    return redirect(url_for('index'))

@app.route('/calender', methods=['GET', 'POST'])
@login_required
def calender():
    if request.method == 'GET':
        return render_template('calender.html', statuses=None)
    else:
        d_date = request.form['d_date']
        cur = g.db.execute('select id, time, content from diary where user_id=? and date=? order by time',(session['user_id'], d_date))
        statuses = cur.fetchall()
        return render_template('calender.html', statuses=statuses, d_date=d_date)

@app.route('/import', methods=['GET', 'POST'])
@login_required
def act_import():
    if request.method == 'GET':
        return render_template('act_import.html')
    else:
        diaries = []
        tag = request.form['tag']
        lookup_tag = "#" + tag + "#"
        page = int(request.form['page'])
        handler = fanfou.get_session((session['access_token'], session['access_token_secret']))
        for count in range(1, page+1):
            resp = handler.get('statuses/user_timeline.json', params={'page':count,})
            statuses = resp.json()
            for status in statuses:
                if lookup_tag in status['text']:
                    status_text = status['text'].replace(lookup_tag, "")
                    status_dt_utc = parser.parse(status['created_at'])
                    status_dt = status_dt_utc + relativedelta(hours=+8)
                    status_date = status_dt.strftime("%Y-%m-%d")
                    status_time = status_dt.strftime("%H:%M")
                    if 'photo' in status:
                        diaries.append({'date':status_date, 'time':status_time, 'text':status_text, 'photo':status['photo']['thumburl']})
                        g.db.execute("insert into diary (user_id, date, time, content, photo_url) values (?, ?, ?, ?, ?)", \
                            (session['user_id'], status_date, status_time, status_text, status['photo']['thumburl']))
                        g.db.commit()
                    else:
                        diaries.append({'date':status_date, 'time':status_time, 'text':status_text})
                        g.db.execute("insert into diary (user_id, date, time, content) values (?, ?, ?, ?)", \
                            (session['user_id'], status_date, status_time, status_text))
                        g.db.commit()
        return render_template('act_import.html', diaries=diaries)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    cur = g.db.execute("select user_id, fanfou_id from diary where id=?", (id,))
    result = cur.fetchall()[0]
    user_id = result[0]
    fanfou_id = result[1]
    print user_id
    if user_id == session['user_id']:
        g.db.execute("delete from diary where id=?", (id, ))
        g.db.commit()
        handler = fanfou.get_session((session['access_token'], session['access_token_secret']))
        handler.post('statuses/destroy.json', data={'id': fanfou_id, })
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run()
