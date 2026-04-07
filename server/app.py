import sys
import os
sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from datetime import timedelta
from flask import Flask, redirect, session, url_for, render_template, request
from werkzeug.utils import secure_filename
from image_to_desc import describe_image
from song_generator import get_song_list_from_caption
from spotify_handler import search_track_on_spotify, create_playlist_from_song_list, set_playlist_cover, sp_oauth, get_spotify_client

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# store photos in static/uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# session config
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)


@app.route('/')
def home():
    image_filename = session.get('image_filename')
    logged_in = 'token_info' in session
    image_url = None

    # verify file still exists before passing url to template
    if image_filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(file_path):
            image_url = url_for('static', filename=f'uploads/{image_filename}')
        else:
            session.pop('image_filename', None)

    return render_template('home.html', image_url=image_url, logged_in=logged_in)


@app.route('/login')
def login():
    return redirect(sp_oauth.get_authorize_url())


@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('generate_playlist'))


@app.route('/upload', methods=['POST'])
def upload_photo():
    image = request.files['image']
    filename = secure_filename(image.filename)
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    session['image_filename'] = filename
    return redirect(url_for('home'))


@app.route('/generate_playlist')
def generate_playlist():
    if 'token_info' not in session:
        return redirect('/login')
    return handle_playlist_creation()


def get_valid_token():
    token_info = session.get('token_info')
    if not token_info:
        return None
    if sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
        except Exception:
            session.clear()
            return None
    return token_info['access_token']


def handle_playlist_creation():
    try:
        image_filename = session.get('image_filename')
        if not image_filename:
            return "No image uploaded. Please go back and upload one."

        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

        access_token = get_valid_token()
        if not access_token:
            return redirect('/login')

        sp = get_spotify_client(access_token)

        description = describe_image(image_path)
        raw_song_list = get_song_list_from_caption(description)

        # search spotify
        track_uris = []
        for line in raw_song_list[:20]:
            try:
                uri = search_track_on_spotify(sp, line)
                if uri:
                    track_uris.append(uri)
            except Exception:
                continue

        playlist_url = None
        playlist_id = None
        if track_uris:
            try:
                user_id = sp.current_user()['id']
                playlist_url, playlist_id = create_playlist_from_song_list(
                    sp, user_id, f"Photo2Playlist: {description}", track_uris
                )
                set_playlist_cover(sp, playlist_id, image_path)
            except Exception as e:
                return f"Error creating playlist: {str(e)}", 500

        return render_template(
            "playlist.html",
            caption=description,
            tracks_found=len(track_uris),
            playlist_url=playlist_url,
            playlist_id=playlist_id
        )

    except Exception as e:
        return f"An error occurred: {str(e)}", 500


@app.route('/clear')
def clear_session():
    image_filename = session.get('image_filename')
    if image_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        except OSError:
            pass
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
