from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

def describe_image(image_path):
    # 1. Load BLIP model + processor (used for preparing the image & decoding the output)
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    
    # 2. Load the image and convert to RGB
    image = Image.open(image_path).convert('RGB')

    # 3. Tokenize the image for the model
    inputs = processor(image, return_tensors="pt")

    # 4. Generate a caption (in token IDs)
    out = model.generate(**inputs)

    # 5. Decode the tokens into a human-readable string
    description = processor.decode(out[0], skip_special_tokens=True)
    return description