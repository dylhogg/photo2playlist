import base64
import os
from openai import OpenAI

def describe_image(image_path):
    """
    Describe image using OpenAI's GPT-4 Vision API
    No local ML models needed - perfect for deployment!
    """
    
    # Check if file exists
    if not os.path.exists(image_path):
        return "A photo with various visual elements"
    
    # Check if API key is available
    if not os.getenv("OPENAI_API_KEY"):
        return "A photo with various visual elements"
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Read and encode image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper than gpt-4o, excellent quality
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in a way that accurate represents the mood of the image. Describe key elements of the image and use adjectives to represent the mood of the image. Use no more than 12 words or 80 characters."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"  # Reduces cost while maintaining quality
                            }
                        }
                    ]
                }
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        description = response.choices[0].message.content.strip()
        return description
        
    except Exception as e:
        # Fallback description
        return "A photo with various visual elements and atmosphere"