# 🎵 Photo2Playlist

Turn any photo into a personalized Spotify playlist! Upload an image and let AI analyze the mood, atmosphere, and vibes to generate a custom playlist that matches your photo.

## ✨ Features

- **AI-Powered Image Analysis**: Uses BLIP (Bootstrapped Language-Image Pre-training) to understand your photos
- **Smart Music Curation**: GPT generates songs that match the mood and atmosphere of your image
- **Spotify Integration**: Automatically creates playlists in your Spotify account
- **Accurate Song Matching**: Field-specific search ensures you get the right songs by the right artists

## 🚀 How It Works

1. **Upload** your photo
2. **Login** with Spotify
3. **Generate** - AI analyzes your image and creates a matching playlist
4. **Listen** - Your new playlist appears in your Spotify account!

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Spotify Developer Account
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/dylhogg/photo2playlist.git
cd photo2playlist
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
FLASK_SECRET_KEY=your-secret-key
SPOTIPY_CLIENT_ID=your-spotify-client-id
SPOTIPY_CLIENT_SECRET=your-spotify-client-secret
SPOTIPY_REDIRECT_URI= Use an API gateway like ngrok in order to get an https uri for the spotipy callback (spotipy does not accept http protocols)
OPENAI_API_KEY=your-openai-api-key
```

4. Run the app:
```bash
python .\server\app.py
```

Visit your API gateway to start using the app!
