from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
import os

# Global variables to cache the model (avoid reloading every time)
_processor = None
_model = None

def get_model_and_processor():
    """Load and cache the model and processor"""
    global _processor, _model
    
    if _processor is None or _model is None:
        print("Loading BLIP model...")
        # Add use_fast=True to fix the slow processor warning
        _processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base", 
            use_fast=True
        )
        _model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
        print("Model loaded successfully")
    
    return _processor, _model

def describe_image(image_path):
    try:
        
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load cached model and processor
        processor, model = get_model_and_processor()
        
        # Load the image and convert to RGB
        image = Image.open(image_path).convert('RGB')
        
        # Resize image if too large (speeds up processing)
        max_size = 512
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Tokenize the image for the model
        inputs = processor(image, return_tensors="pt")

        # Generate a caption with limited length (faster generation)
        with torch.no_grad():  # Disable gradient computation for inference
            out = model.generate(
                **inputs,
                max_length=50,  # Limit output length
                num_beams=3,    # Reduce beam search (faster but slightly less quality)
                early_stopping=True
            )

        # Decode the tokens into a human-readable string
        description = processor.decode(out[0], skip_special_tokens=True)
        
        return description
        
    except Exception as e:
        # Return a fallback description instead of crashing
        return "A photo with various visual elements"