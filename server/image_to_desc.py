import base64
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

fallback = "A photo with various visual elements"

def describe_image(image_path):
    if not os.path.exists(image_path) or not os.getenv("OPENAI_API_KEY"):
        return fallback
    try:
        # encoding
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in a way that accurately represents the mood. Describe key elements and use adjectives. Use no more than 12 words or 80 characters."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low"
                        }
                    }
                ]
            }],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return fallback
