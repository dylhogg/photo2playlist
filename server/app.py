import sys
import os
sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

#Flask app
import re
import time
from flask import Flask, request, jsonify, redirect, session, url_for, render_template
from image_to_desc import describe_image
from song_generator import get_song_list_from_caption
from spotify_handler import search_track_on_spotify, create_playlist_from_song_list, sp_oauth, get_spotify_client
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Use paths relative to the Flask app location
STATIC_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')

# Create the directory
os.makedirs(STATIC_UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = STATIC_UPLOAD_FOLDER

@app.route('/')
def home():
    # Get both the full path and relative path from session
    image_filename = session.get('image_filename')
    logged_in = 'token_info' in session

    # Create the web-accessible URL if image exists
    image_url = None
    if image_filename:
        image_url = url_for('static', filename=f'uploads/{image_filename}')

    return render_template('home.html', image_url=image_url, logged_in=logged_in)

@app.route('/login')
def login():
    return redirect(sp_oauth.get_authorize_url())

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    
    # Store the full token info, including refresh token
    session['token_info'] = token_info

    # After login, continue to playlist generation
    return redirect(url_for('generate_playlist'))

@app.route('/upload', methods=['POST'])
def upload_photo():
    image = request.files['image']
    filename = image.filename
    
    # Save to the static/uploads folder within your app directory
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # The directory should already exist, but just in case
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    
    image.save(image_path)

    # Store relative path for processing and filename for URL generation
    session['image_path'] = image_path  # Full path for backend processing
    session['image_filename'] = filename

    return redirect(url_for('home'))

@app.route('/generate_playlist')
def generate_playlist():
    # If not logged in with Spotify, redirect to login
    if 'token_info' not in session:
        return redirect('/login')
    
    # Otherwise, process image and generate playlist
    return handle_playlist_creation()

def get_valid_token():
    """Get a valid access token, refreshing if necessary"""
    token_info = session.get('token_info')
    
    if not token_info:
        return None
    
    # Check if token is expired and refresh if needed
    if sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
        except Exception as e:
            # Clear session and force re-login
            session.clear()
            return None
    
    return token_info['access_token']

def handle_playlist_creation():
    try:
        # Use the full path for image processing
        image_path = session.get('image_path')
        if not image_path:
            return "No image uploaded. Please go back and upload one."

        # Get a valid access token (will refresh if needed)
        access_token = get_valid_token()
        if not access_token:
            return redirect('/login')
        
        sp = get_spotify_client(access_token)

        # Pass the full path to describe_image
        description = describe_image(image_path)
        raw_song_list = get_song_list_from_caption(description)
        track_uris = []
        
        # Limit to first 20 songs to avoid timeout
        for i, line in enumerate(raw_song_list[:20]):
            try:
                uri = search_track_on_spotify(sp, line)
                if uri:
                    track_uris.append(uri)
            except Exception as e:
                continue

        playlist_url = None
        playlist_id = None
        
        if track_uris:
            try:
                user_id = sp.current_user()['id']
                playlist_url, playlist_id = create_playlist_from_song_list(sp, user_id, f"Photo2Playlist: {description}", track_uris)
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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))