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
    
    print(f"Image saved to: {image_path}")  # Debug line

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
            print(f"Error refreshing token: {e}")
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

        print("Starting image description...")
        # Pass the full path to describe_image
        description = describe_image(image_path)
        print(f"Image description: {description}")
        
        print("Getting song list...")
        raw_song_list = get_song_list_from_caption(description)
        print(f"Got {len(raw_song_list)} songs")

        track_uris = []
        print("Searching for tracks on Spotify...")
        
        # Limit to first 20 songs to avoid timeout
        for i, line in enumerate(raw_song_list[:20]):
            try:
                print(f"Searching for track {i+1}: {line}")
                uri = search_track_on_spotify(sp, line)
                if uri:
                    track_uris.append(uri)
                    print(f"Found: {uri}")
            except Exception as e:
                print(f"Error searching for track '{line}': {e}")
                continue

        playlist_url = None
        playlist_id = None
        
        if track_uris:
            try:
                print(f"Creating playlist with {len(track_uris)} tracks...")
                user_id = sp.current_user()['id']
                playlist_url, playlist_id = create_playlist_from_song_list(sp, user_id, f"Photo2Playlist: {description}", track_uris)
                print(f"Playlist created: {playlist_url}")
            except Exception as e:
                print(f"Error creating playlist: {e}")
                return f"Error creating playlist: {str(e)}", 500
        else:
            print("No tracks found")

        return render_template(
            "playlist.html",
            caption=description,
            tracks_found=len(track_uris),
            playlist_url=playlist_url,
            playlist_id=playlist_id
        )
        
    except Exception as e:
        print(f"Error in playlist creation: {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred: {str(e)}", 500
    
@app.route('/test_playlist')
def test_playlist():
    """Create a test playlist with known popular songs"""
    
    # Check if logged in
    if 'token_info' not in session:
        return redirect('/login')
    
    # Get valid token
    access_token = get_valid_token()
    if not access_token:
        return redirect('/login')
    
    sp = get_spotify_client(access_token)
    
    # List of guaranteed popular songs
    test_songs = [
        "Bohemian Rhapsody - Queen",
        "Hotel California - Eagles", 
        "Sweet Child O' Mine - Guns N' Roses",
        "Imagine - John Lennon",
        "Billie Jean - Michael Jackson",
        "Shape of You - Ed Sheeran",
        "Blinding Lights - The Weeknd",
        "As It Was - Harry Styles",
        "Don't Stop Believin' - Journey",
        "Stairway to Heaven - Led Zeppelin"
    ]
    
    print(f"TEST PLAYLIST: Starting with {len(test_songs)} songs")
    
    track_uris = []
    search_results = []
    
    # Search for each song
    for i, song in enumerate(test_songs):
        try:
            print(f"Searching for song {i+1}/{len(test_songs)}: {song}")
            uri = search_track_on_spotify(sp, song)
            
            result = {
                'song': song,
                'found': bool(uri),
                'uri': uri
            }
            
            if uri:
                track_uris.append(uri)
                print(f"  ✅ Found: {uri}")
            else:
                print(f"  ❌ Not found")
            
            search_results.append(result)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            search_results.append({
                'song': song,
                'found': False,
                'error': str(e)
            })
    
    print(f"TEST PLAYLIST: Found {len(track_uris)} out of {len(test_songs)} tracks")
    
    # Create playlist if we found tracks
    playlist_url = None
    playlist_id = None
    
    if track_uris:
        try:
            user_id = sp.current_user()['id']
            playlist_name = f"Test Playlist - {len(track_uris)} tracks"
            
            print(f"Creating playlist '{playlist_name}' for user {user_id}")
            playlist_url, playlist_id = create_playlist_from_song_list(
                sp, user_id, playlist_name, track_uris
            )
            print(f"Playlist created: {playlist_url}")
            
        except Exception as e:
            print(f"Error creating playlist: {e}")
            return {
                'error': f'Failed to create playlist: {str(e)}',
                'search_results': search_results,
                'tracks_found': len(track_uris),
                'device_info': request.headers.get('User-Agent')
            }
    
    # Return results
    return render_template(
        "playlist.html",
        caption=f"Test playlist with popular songs",
        tracks_found=len(track_uris),
        playlist_url=playlist_url,
        playlist_id=playlist_id
    )

@app.route('/test_playlist_json')
def test_playlist_json():
    """Same test but returns JSON results for debugging"""
    
    # Check if logged in
    if 'token_info' not in session:
        return {'error': 'Not logged into Spotify', 'login_url': '/login'}
    
    # Get valid token
    access_token = get_valid_token()
    if not access_token:
        return {'error': 'Failed to get valid token', 'login_url': '/login'}
    
    sp = get_spotify_client(access_token)
    
    # Test songs
    test_songs = [
        "Bohemian Rhapsody - Queen",
        "Hotel California - Eagles", 
        "Sweet Child O' Mine - Guns N' Roses",
        "Imagine - John Lennon",
        "Billie Jean - Michael Jackson"
    ]
    
    results = {
        'device_info': {
            'user_agent': request.headers.get('User-Agent'),
            'remote_ip': request.remote_addr,
            'is_mobile': 'Mobile' in request.headers.get('User-Agent', '')
        },
        'user_info': {},
        'search_results': [],
        'playlist_info': {}
    }
    
    try:
        # Get user info
        user = sp.current_user()
        results['user_info'] = {
            'id': user['id'],
            'display_name': user.get('display_name'),
            'country': user.get('country'),
            'product': user.get('product')
        }
    except Exception as e:
        results['user_info'] = {'error': str(e)}
    
    # Test searches
    track_uris = []
    
    for song in test_songs:
        try:
            start_time = time.time()
            uri = search_track_on_spotify(sp, song)
            search_time = time.time() - start_time
            
            result = {
                'song': song,
                'found': bool(uri),
                'uri': uri,
                'search_duration': round(search_time, 3)
            }
            
            if uri:
                track_uris.append(uri)
            
            results['search_results'].append(result)
            
        except Exception as e:
            results['search_results'].append({
                'song': song,
                'found': False,
                'error': str(e),
                'search_duration': 0
            })
    
    # Summary
    results['summary'] = {
        'total_songs': len(test_songs),
        'found_songs': len(track_uris),
        'success_rate': round(len(track_uris) / len(test_songs) * 100, 1),
        'avg_search_time': round(
            sum(r.get('search_duration', 0) for r in results['search_results']) / len(results['search_results']),
            3
        ) if results['search_results'] else 0
    }
    
    # Try to create playlist
    if track_uris:
        try:
            user_id = results['user_info']['id']
            playlist_name = f"Test - {len(track_uris)} tracks"
            
            playlist_url, playlist_id = create_playlist_from_song_list(
                sp, user_id, playlist_name, track_uris
            )
            
            results['playlist_info'] = {
                'success': True,
                'playlist_url': playlist_url,
                'playlist_id': playlist_id,
                'tracks_added': len(track_uris)
            }
            
        except Exception as e:
            results['playlist_info'] = {
                'success': False,
                'error': str(e)
            }
    else:
        results['playlist_info'] = {
            'success': False,
            'reason': 'No tracks found to add'
        }
    
    return results


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))