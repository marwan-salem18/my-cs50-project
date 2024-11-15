import os
from cs50 import SQL
from pathlib import Path
from flask import Flask, flash, jsonify, redirect, render_template, request, session, g
from flask_session import Session
from functools import wraps

# could've made anything else

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///flasktube.db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def index():
    videos = db.execute("SELECT id,video_name,img_location FROM videos")
    return render_template("index.html",videos=videos)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        video = request.files['video']
        if not video:
            return render_template("error.html",error ='no video')
        
        thumbnail = request.files['thumbnail']
        if not thumbnail:
            return render_template("error.html",error ='no thumbnail')
        
        title = request.form.get("title")
        if not title:
            return render_template("error.html",error ='no title')

        try : 
            id = db.execute("SELECT id FROM videos ORDER BY id DESC LIMIT 1")[0]["id"]
            id = id+1

        except IndexError: id = 1

        img_name = thumbnail.filename

        allowed_img_extension = [".png",".jpg","jpeg"]
        img_extension = os.path.splitext(img_name)[1]
        if img_extension not in allowed_img_extension:
            return render_template("error.html",error ='invaild img')
        
        img_path = "static/thumbnails"

        img_path = f"{img_path}/{id}{img_extension}"

        vid_name = video.filename

        vid_extension = os.path.splitext(vid_name)[1]
        if vid_extension != ".mp4":
             return render_template("error.html",error ='invaild video')

        vid_path = "static/videos"

        vid_path = f"{vid_path}/{id}{vid_extension}"

        with open(img_path,'wb') as file:
            file.write(thumbnail.read())
        with open(vid_path,'wb') as file:
            file.write(video.read())

        db.execute("INSERT INTO videos (user_id,video_name,video_location,img_location) VALUES(?,?,?,?)", session['user_id'],title,vid_path,img_path)

        return redirect("/")
    
    else: 
        return render_template("upload.html")
    
@app.route("/videoplayer")
def videoplayer():
    name = request.args.get("name")

    try :
        main_video = db.execute("SELECT id,video_name,video_location FROM videos WHERE id = (?)",name)[0]
    except IndexError:
        return render_template("error.html",error ='invaild video')

    videos = db.execute("SELECT id,video_name,img_location FROM videos WHERE id != (?)",name)

    return render_template("/videoplayer.html",main_video=main_video,videos=videos)

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template("error.html",error ="must provide username")

        elif not request.form.get("password"):
            return render_template("error.html",error ="must provide password")

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) != 1 or not rows[0]["password"] == request.form.get("password"):
            return render_template("error.html",error ="invalid username and/or password")

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("username")

        if not name:
            return  render_template("error.html",error ="empty username")
        password = request.form.get("password")

        if not password:
            return render_template("error.html",error ="empty password")
        confirm = request.form.get("confirmation")

        if not confirm:
            return render_template("error.html",error ="empty confirmation")
        
        if password != confirm:
            return render_template("error.html",error ="password doesn't match confirmation")
        
        hash = password

        try:
            db.execute("INSERT INTO users (username, password) VALUES(?, ?)", name, hash)

        except ValueError:
            return render_template("error.html",error ="username alredy taken")
        
        ses = db.execute("SELECT id FROM users WHERE username = ?", name)

        ses = ses[0]

        session['user_id'] = ses['id']

        return redirect("/")
    
    else:
        return render_template("register.html")
    
@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    if request.method == "POST":

        username = request.form.get("username")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) < 1:
            return ("input a vaild username")
        
        if username != (db.execute("SELECT username FROM users WHERE id = ?", session['user_id'])[0]['username']):
            return render_template("error.html",error = "username doesn't match")
        
        old_password = request.form.get("old_password")

        if  rows[0]["password"]  != old_password:
            return render_template("error.html",error ="password doesn't match")
        
        new_password = request.form.get("new_password")

        if not new_password:
            return render_template("error.html",error ="empty new password")
        
        confirm = request.form.get("confirm")

        if not confirm:
            return render_template("error.html",error ="empty confirm")
        
        if new_password != confirm:
            return render_template("error.html",error ="new password doesn't match confirmation")
        
        if new_password == old_password:
            return render_template("error.html",error ="new password can't be the same as the old one")

        db.execute("UPDATE users SET password = (?) WHERE username = (?)", new_password, username)

        return redirect("/")
    
    else:
        return render_template("password.html")

@app.route("/search")
def search():
    searched = request.args.get("search")
    if not searched:
        return redirect("/")
    search_term = "%" + searched + "%"
    videos = db.execute("SELECT * FROM videos WHERE video_name LIKE ?",search_term)

    return render_template("search.html",videos=videos)

@app.route("/videos", methods=["GET", "POST"])
@login_required
def videos():
    videos = db.execute("SELECT * FROM videos WHERE user_id = ?",session['user_id'])
    if request.method == "POST":
        delete = request.form.get("video_id")
        try: 
            files = db.execute("SELECT img_location,video_location FROM videos WHERE id = ?" ,delete)[0]
        except IndexError: return render_template("error.html",error ='invaild video')

        os.remove(files['img_location'])

        os.remove(files['video_location'])

        db.execute("DELETE FROM videos WHERE id = ?",delete)
        
        return render_template("videos.html",videos=videos)
    
    else:    
        return render_template("videos.html",videos=videos)
        