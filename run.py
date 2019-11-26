# all the imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, send_file, send_from_directory
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

# configuration
UPLOAD_FOLDER = 'static/music'
ALLOWED_EXTENSIONS = set(['mp3', 'wav'])
DATABASE = 'database.db'
DEBUG = True
SECRET_KEY = 'development key'
#USERNAME = 'admin'
#PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)
#app.config.from_envvar('FLASKR_SETTINGS', silent=True)
# в FLASKR_SETTINGS название конфигурационного файла

#globals
nn=None
m_file=None
sql_1='SELECT m_id, IFNULL(track_id,0) AS favor, m_path, m_name, ms_name, m_style, artist FROM m_files JOIN m_styles ON m_style=ms_id LEFT OUTER JOIN (SELECT * FROM favorit WHERE user_id=0) ON m_id=track_id WHERE 1=1'
#sql_1='SELECT m_id, m_favor, m_path, m_name, ms_name, m_style FROM  m_files INNER JOIN m_styles ON m_style=ms_id WHERE 1=1'
sql_2=''
sql_=sql_1+sql_2


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def get_db():
    con=sqlite3.connect(app.config['DATABASE'])
    return con

#def init_db():
#    db = get_db()
#    with app.open_resource('schema.sql') as f:
#        db.executescript(f.read().decode('utf8'))
#>>> from run import init_db
#>>> init_db()

@app.before_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    global sql_
    global sql_1
    global sql_2
    user_id = session.get("user_id") or 0
    if user_id == 0: #is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )
    sql_1='SELECT m_id, IFNULL(track_id,0) AS favor, m_path, m_name, ms_name, m_style, artist FROM m_files JOIN m_styles ON m_style=ms_id LEFT OUTER JOIN (SELECT * FROM favorit WHERE user_id={}) ON m_id=track_id WHERE 1=1'.format(user_id)
    sql_=sql_1+sql_2

@app.before_request
def before_request():
    g.db = get_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()
    
@app.route('/')
def show_tracks():
    global m_file
    global sql_
    global nn
    cur = g.db.execute(sql_)
    tracks = [dict(id = row[0], m_name=row[3], m_favor=row[1], ms_name=row[4], m_style=row[5], artist=row[6] ) for row in cur.fetchall()]
    cur = g.db.execute('select ms_id, ms_name from m_styles')
    styles = [dict(id = row[0], name=row[1]) for row in cur.fetchall()]
    return render_template('show_tracks.html', tracks=tracks, styles=styles, m_file=m_file, id=nn)

@app.route('/add', methods=['GET', 'POST'])
def add():
    cur = g.db.execute('select ms_id, ms_name from m_styles')
    styles = [dict(id = row[0], name=row[1]) for row in cur.fetchall()]
    if request.method == 'POST': 
        # check if the post request has the file part
        if 'file' not in request.files: 
            flash('No file part') 
            return redirect(request.url) 
        file =  request.files['file'] 
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '': 
            flash( 'No selected file') 
            return redirect( request.url) 
        if file and allowed_file(file.filename): 
            filename =  secure_filename(file.filename) 
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],  filename))
            cur = g.db.execute('INSERT INTO m_files (m_name, m_style, m_path, artist, album, about) VALUES (?, ?, ?, ?, ?, ?)', \
                [request.form['name'] or filename, request.form['style'], filename, request.form['artist'], request.form['album'], request.form['about']])
            g.db.commit()
            flash('Ok')
        else:
            flash('Error')
    return render_template('add.html', styles=styles)           
    
@app.route('/play/<int:n>', methods=['GET', 'POST'])
def play_track(n):
    global m_file
    global nn
    nn=n
    cur=g.db.execute('select m_name, m_path, artist, album, about from m_files where m_id=?', [n,])
    row = cur.fetchone()
    m_file=list(row)
    #print(m_file[1])
    m_file.append(os.path.join(app.config['UPLOAD_FOLDER'],"".join(row[1])))
#    print(m_file)

    flash(row[0])
    return redirect(url_for('show_tracks'))
    #return redirect(url_for('static', filename='play.html'), m_file=m_file, id=nn)
 
@app.route('/edit/<int:n>', methods=['GET', 'POST'])
def edit(n):
    if session['user_id'] == 1:
        #редактирование
        cur = g.db.execute('SELECT m_id, m_path, m_name, m_style, artist, album, about FROM m_files WHERE m_id=?',[n,])
        track = cur.fetchone()
        #print(track)
        cur = g.db.execute('select ms_id, ms_name from m_styles')
        styles = [dict(id = row[0], name=row[1]) for row in cur.fetchall()]
        if request.method=='POST':
            cur = g.db.execute('UPDATE m_files SET m_name=?, m_style=?, artist=?, album=?, about=? WHERE m_id=?', \
                [request.form['name'], request.form['style'], request.form['artist'], request.form['album'], request.form['about'], n])
            g.db.commit()            
            return redirect(url_for('show_tracks'))
        return render_template('edit.html', track=track, styles=styles)
    return redirect(url_for('show_tracks'))

@app.route('/del/<int:n>', methods=['POST'])
def delete(n):
    if session['user_id'] == 1:
        nn=None
        m_file=None
        cur=g.db.execute('select m_path from m_files where m_id=?', [n,])
        row=cur.fetchone()
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],  "".join(row[0])))
        except:
            pass
        finally:
            g.db.execute('DELETE FROM m_files WHERE m_id=?', [n,])
            g.db.commit()
    return redirect(url_for('show_tracks'))

@app.route('/download/<int:n>')
def download(n):
    cur=g.db.execute('select m_name, m_path from m_files where m_id=?', [n,])
    row=cur.fetchone()
    #pth=os.path.join( app.config['UPLOAD_FOLDER'] , "".join(row[1])
    fn= "".join( row[1] )
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename = fn, as_attachment=True)
    #return redirect(url_for('show_tracks'))
    
@app.route('/fav/<int:n>')
def fav(n):
    cur=g.db.execute('select * from favorit where track_id=? and user_id=?', [n,g.user[0]])
    row = cur.fetchone()
    if row:
        g.db.execute('delete from favorit where track_id=? and user_id=?', [n,g.user[0]])
        g.db.commit()
    else:
        g.db.execute('insert into favorit (track_id, user_id) values (?, ?)', [n,g.user[0]])
        g.db.commit()
    return redirect(url_for('show_tracks'))

#Фильтрация####################################################################################
@app.route('/Clear', methods=['POST'])
def Cl_filter():
    global sql_2
    sql_2=''
    flash('Фильтр отключен')
    return redirect(url_for('show_tracks'))

@app.route('/style/<int:n>')
def style(n):
    global sql_2
    sql_2=sql_2+' and m_style ='+ str(n)
    flash('Фильтр = "{}"'.format(n))
    return redirect(url_for('show_tracks'))

@app.route('/style2/<int:n>', methods=['POST'])
def style2(n):
    global sql_2
    for i in sql_2.split(' and '):
        if i[0:4]=='m_st':
            sql_2 = sql_2.replace(i,'m_style ='+ str(n))
            flash('Фильтр = "{}"'.format(n))
            return redirect(url_for('show_tracks'))
    sql_2=sql_2+' and m_style ='+ str(n)
    flash('Фильтр = "{}"'.format(n))
    return redirect(url_for('show_tracks'))

@app.route('/find', methods=['POST'])
def find():
    global sql_2
    s=request.form['tr_name']
    if s:
        for i in sql_2.split(' and '):
#            print(i[0:4])
            if i[0:4]=='m_na':
                sql_2 = sql_2.replace(i,'m_name like "%'+ s +'%"')
                flash('Фильтр = "{}"'.format(s))
                return redirect(url_for('show_tracks'))
        sql_2=sql_2+' and m_name like "%'+ s +'%"'
        flash('Фильтр = "{}"'.format(s))
    else:
        sql_2=''
        flash('Фильтр отключен')
    return redirect(url_for('show_tracks'))

@app.route('/sel_fav', methods=['POST'])
def sel_fav():
    global sql_2
    sql_2=sql_2 + ' and favor <> 0'
    #print(sql_2)
    flash('Фильтр по избраным')
    return redirect(url_for('show_tracks'))


    
#Users###################################################################################################    
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a registered user by adding the user id to the session."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
#        db = get_db()
        error = None
        user = g.db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user[2], password):
            error = "Incorrect password."

        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            session["user_id"] = user[0]
            g.user = user
            return redirect(url_for("show_tracks"))

        flash(error)

    return render_template("login.html")

@app.route("/register", methods=("GET", "POST"))
def register():
    """Register a new user.

    Validates that the username is not already taken. Hashes the
    password for security.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
#        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif (
            g.db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
            is not None
        ):
            error = "User {0} is already registered.".format(username)

        if error is None:
            # the name is available, store it in the database and go to
            # the login page
            g.db.execute(
                "INSERT INTO user (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            g.db.commit()
            return redirect(url_for("login"))

        flash(error)

    return render_template("register.html")



@app.route('/logout')
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    g.user = None
    flash('You were logged out')
    return redirect(url_for('show_tracks'))
    
if __name__ == '__main__':
    app.run(port=3000)
    
