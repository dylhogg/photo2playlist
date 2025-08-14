from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def get_song_list_from_caption(caption):

    
    prompt = f"""
You are a music curator. Based on this scene description: "{caption}", suggest 20 real songs that match the mood and atmosphere.

Format each song exactly like this example:
Bohemian Rhapsody - Queen
Hotel California - Eagles
Sweet Child O' Mine - Guns N' Roses

IMPORTANT: 
- Use exactly the format "Song Title - Artist"
- Do NOT use numbers (1., 2., 3., etc.)
- Do NOT use bullet points or dashes at the start
- Each song on its own line
- Return ONLY the song list, no other text
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )

    text = response.choices[0].message.content
    return text.strip().split("\n")
