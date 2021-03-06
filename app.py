from flask import Flask, request, redirect, session, render_template, Response
from werkzeug import secure_filename
import time
import psycopg2 as dbapi2

import memeMatcher

import os
import json
import sqlite3


app = Flask(__name__)

def lookup_by_song_id(song_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT * from upload WHERE id=%s", (song_id, ))
    filename = cur.fetchone()[1]
    return base_path() + "/tmp/" + filename

def memes(song_file):
    a = memeMatcher.memeMatcher(song_file)
    return a.timings, a.title, a.artist

def intro_time(song_file):
    return 0

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def base_path():
    return os.path.dirname(os.path.realpath(__file__))

def read_template(template_name, params={}):
    return render_template(template_name, **params)

def database_connection():
    return dbapi2.connect (database="burns", user="burns", password="lol", host="127.0.0.1")

def favourite_tracks():
    ids = [1, 8, 9, 106, 109]
    results = []
    for oid in ids:
        song_file = lookup_by_song_id(oid)
        a = memeMatcher.memeMatcher(song_file)
        artist = a.artist
        title = a.title
        results.append({"id": oid, "artist": artist, "title":title})

    return results


def most_recent_tracks():
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT * from upload order by id DESC limit 5")
    results = []
    for row in cur:
        song_file = base_path() + "/tmp/" + row[1]
        try:
            a = memeMatcher.memeMatcher(song_file)
            artist = a.artist
            title = a.title
            results.append({"id": row[0], "artist": artist, "title":title})
        except Exception as e:
            pass
            #print e

    return results

cache, last_cache_at = None, 0


@app.route("/")
def hello():
    global cache
    global last_cache_at
    t = time.time()
    if t - last_cache_at > 600:
        cache = read_template("index.html",
            {
                "error": session.get("error", None),
                "favourites": favourite_tracks(),
                "recent": most_recent_tracks(),
            })

        last_cache_at = time.time()
    return cache

@app.route("/audio_files/<file_name>")
def play_song(file_name):
    #TODO: correct mime type
    return Response(open(base_path() + "/tmp/" + file_name).read(), mimetype='audio/mpeg')

@app.route("/upload", methods=["POST"])
def upload():
    global last_cache_at
    last_cache_at = 0
    #print request.files
    session["error"] = None
    uploaded_file = request.files['file']
    if allowed_file(uploaded_file.filename):
        filename = secure_filename(uploaded_file.filename)
        song_path = base_path() + "/tmp/" + filename
        uploaded_file.save(song_path)
        session["song_path"] = song_path
        conn = database_connection()
        cur = conn.cursor()
        cur.execute("SELECT * from upload WHERE file_name=%s", (filename, ))

        row = cur.fetchone()
        if not cur.fetchone():
            cur.execute("INSERT INTO upload (file_name) values(%s)", (filename,))
            conn.commit()
            cur.execute("SELECT id from upload WHERE file_name=%s", (filename,))
            row = cur.fetchone()
            song_id = str(row[0])
        else:
            song_id = str(row[0])

        return redirect("/player?song_id=" + str(song_id))

    session["error"] = "uploaded file of wrong type"
    return redirect("/")

@app.route("/player", methods=["GET"])
def player():
    song_path = lookup_by_song_id(request.args.get("song_id"))
    http_song_path = "/audio_files/" + os.path.split(song_path)[-1]
    meme_list, title, artist = memes(song_path)
    text = '"' + title + '" by ' + artist
    if len(text) > 50:
        text = ""
    return read_template("player.html", {
        "song_path": http_song_path,
        "mime_type": "audio/mpeg",
        "memes":json.dumps(meme_list),
        "flavour":text,
        "intro_time": intro_time(open(song_path)),
    })

upload_folder = base_path() + "/tmp/"
UPLOAD_FOLDER = ''
ALLOWED_EXTENSIONS = set(["mp3", "wav", "ogg", "m4a"])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "adofijqweofijsdfklgjasdflidqogjwiodf:w"
app.debug = True

if __name__ == "__main__":
    app.run(threaded=True)
