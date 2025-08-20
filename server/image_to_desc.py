from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
import os

# Global variables to cache the model (avoid reloading every time)
_processor = None
_model = None

def get_model_and_processor():
    """Load and cache a lightweight model and processor"""
    global _processor, _model
    
    if _processor is None or _model is None:
        
        # Use the smaller BLIP model that's more memory efficient
        model_name = "nlpconnect/vit-gpt2-image-captioning"
        
        try:
            from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
            
            _model = VisionEncoderDecoderModel.from_pretrained(model_name)
            _processor = ViTImageProcessor.from_pretrained(model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Set to evaluation mode to save memory
            _model.eval()
            torch.set_grad_enabled(False)
            
            return _processor, _model, tokenizer
            
        except Exception as e:
            # Fallback to original BLIP but with optimizations
            _processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base", 
                use_fast=True
            )
            _model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            _model.eval()
            torch.set_grad_enabled(False)
    
    return _processor, _model, None

def describe_image(image_path):
    try:
        
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load cached model and processor
        result = get_model_and_processor()
        if len(result) == 3:  # Lightweight model
            processor, model, tokenizer = result
            use_lightweight = True
        else:  # BLIP fallback
            processor, model = result
            tokenizer = None
            use_lightweight = False
        
        # Load and process image
        image = Image.open(image_path).convert('RGB')
        
        # Resize image if too large (speeds up processing and saves memory)
        max_size = 384  # Smaller size for memory efficiency
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        with torch.no_grad():
            if use_lightweight:
                # Use the lightweight ViT-GPT2 model
                pixel_values = processor(images=image, return_tensors="pt").pixel_values
                output_ids = model.generate(
                    pixel_values, 
                    max_length=25, 
                    num_beams=2,
                    early_stopping=True
                )
                description = tokenizer.decode(output_ids[0], skip_special_tokens=True)
            else:
                # Use BLIP model
                inputs = processor(image, return_tensors="pt")
                out = model.generate(
                    **inputs,
                    max_length=25,  # Short output for speed
                    num_beams=2,    # Minimal beams for memory
                    early_stopping=True,
                    do_sample=False
                )
                description = processor.decode(out[0], skip_special_tokens=True)
        
        print(f"Generated description: {description}")
        return description.strip()
        
    except Exception as e:
        print(f"Error in describe_image: {e}")
        import traceback
        traceback.print_exc()
        # Return a fallback description instead of crashing
        return "A photo with various visual elements"