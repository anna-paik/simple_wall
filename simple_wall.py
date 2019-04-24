from flask import Flask, render_template, redirect, request, session, flash
import re
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$")
from mysqlconnection import connectToMySQL
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'Jquery'

@app.route('/')
def index():   
    if 'email' not in session: 
        session['email'] = ''
    if 'first_name' not in session: 
        session['first_name'] = ''
    return render_template('simple_wall.html')

@app.route('/process', methods=['POST'])
def process():
    if len(request.form['first_name']) < 2:
        flash('First name must contain at least two letters and contain only letters', 'first_name')
    if len(request.form['first_name']) < 1: 
        flash('This field is required')
    if len(request.form['last_name']) < 2:
        flash('Last name must contain at least two letters and contain only letters', 'last_name')
    if len(request.form['email']) < 1:
        flash('This field is required', 'email')
    if not EMAIL_REGEX.match(request.form['email']):
        flash('Invalid email address', 'email') 
    if len(request.form['password']) < 1:
        flash('This field is required', 'password')
    if not PASSWORD_REGEX.match(request.form['password']):
        flash("Password must contain a number, a capital letter, and be between 8-15 characters", 'password')
    elif len(request.form['password']) < 8 or len(request.form['password']) > 15:
        flash("Password must contain a number, a capital letter, and be between 8-15 characters", 'password')    
    if  request.form['password'] != request.form['confirm_password']:
        flash("Passwords must match", 'confirm_password')   
    if '_flashes' in session.keys():
        return redirect("/")

    else:
        session['first_name'] = request.form['first_name']
        #pw_hash = bcrypt.generate_password_hash(request.form['password'])
        mysql = connectToMySQL('simple_wall') 
        query = 'insert into users (first_name, last_name, email, password, created_at, updated_at) VALUES (%(first_name)s, %(last_name)s, %(email)s, %(password_hash)s, NOW(), NOW());'
        data = {
            'first_name' : request.form['first_name'],
            'last_name' : request.form['last_name'],
            'email' : request.form['email'],
            'password_hash' : bcrypt.generate_password_hash(request.form['password'])
        }
        new_user = mysql.query_db(query, data)
        session['userid'] = new_user
        session['first_name'] = request.form['first_name']
        return redirect("/success")

@app.route('/success')
def show():
    mysql = connectToMySQL('simple_wall')
    query = 'select messages.message, users.first_name, messages.id as message_id, users.id, messages.created_at,  messages.sender_id FROM users join messages on users.id = messages.sender_id where messages.recipient_id = %(recip)s;'
    data = {
        'recip' : session['userid']
    }
    messages = mysql.query_db(query,data)

    mysql = connectToMySQL('simple_wall')
    query = 'select * from users;'
    users = mysql.query_db(query)

    mysql = connectToMySQL('simple_wall')
    query = 'select * from messages where sender_id = (%(id)s);'
    data = {
        'id': session['userid']
    }
    count_message = mysql.query_db(query, data)
    x = len(count_message)

    mysql = connectToMySQL('simple_wall')
    query = 'select * from messages where recipient_id = (%(id)s);'
    data = {
        'id': session['userid']
    }
    display_message = mysql.query_db(query, data)
    y = len(display_message)

    mysql = connectToMySQL('simple_wall')
    query = 'select * from messages'
    message_display = mysql.query_db(query)  

    return render_template('success_login_wall.html', texts= messages, users = users, x=x, y=y)

@app.template_filter('duration_elapsed')
def timesince(dt, default='just now'):
    now = datetime.now()
    diff = now - dt

    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )
    for period, singular, plural in periods:
        if period: 
            return "%d %s ago" % (period, singular if period == 1 else plural)
    return default
    
@app.route('/login', methods=['POST'])
def login():
    mysql = connectToMySQL('simple_wall')
    query = 'select * FROM users WHERE email = %(email)s;'
    data = {
        'email' : request.form['email']
    }
    result = mysql.query_db(query, data)
    if result: 
        if bcrypt.check_password_hash(result[0]['password'], request.form['login_password']):
            session['userid'] = result[0]['id']
            session['first_name'] = result[0]['first_name']

            return redirect('/success')
        flash("You could not be logged in",'login_password')    
    return redirect('/')


@app.route('/create_message', methods=['POST'])
def send_message():
    mysql = connectToMySQL('simple_wall')
    query = 'insert INTO messages (message, recipient_id, sender_id, created_at, updated_at) VALUES (%(message)s, %(recipient_id)s, %(sender_id)s, NOW(), NOW());'
    data = {
        'message' : request.form['send'],
        'recipient_id' : request.form['recipient_id'],
        'sender_id' : session['userid']
    }
    sent_message = mysql.query_db(query, data)

    return redirect('/success')

@app.route('/delete', methods=['POST'])
def delete():
    mysql = connectToMySQL('simple_wall')
    query = 'delete from messages WHERE sender_id = %(sender_id)s and recipient_id=%(recipient_id)s and messages.id=%(message_id)s;'
    data = {
        'sender_id' : request.form['sender_id'],
        'recipient_id' : session['userid'],
        'message_id' : request.form['message_id']
    } 
    new_delete = mysql.query_db(query,data)
    return redirect('/success')

@app.route('/logout')
def log_off():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)