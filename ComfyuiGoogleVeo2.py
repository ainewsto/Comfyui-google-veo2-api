import os
import random
import time
import json
import uuid
import folder_paths
from PIL import Image
import comfy.utils
from google import genai
from google.genai import types
from .utils import pil2tensor, tensor2pil


def get_config():
    try:
        config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Comflyapi.json')
        with open(config_path, 'r') as f:  
            config = json.load(f)
        return config
    except:
        return {}

def save_config(config):
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Comflyapi.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)


class ComfyuiGoogleVeo2:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "api_key": ("STRING", {"default": ""}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "person_generation": (["dont_allow", "allow_adult"], {"default": "dont_allow"}),
                "duration_seconds": ("INT", {"default": 8, "min": 5, "max": 8}),
                "number_of_videos": ("INT", {"default": 1, "min": 1, "max": 2}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("video", "video_url", "response")
    FUNCTION = "generate_video"
    CATEGORY = "Comfyui-Google-veo2"

    def __init__(self):
        self.google_api_key = self.get_google_api_key()
        self.timeout = 600  

    def get_google_api_key(self):
        config = get_config()
        return config.get('google_api_key', '')

    def save_google_api_key(self, api_key):
        config = get_config()
        config['google_api_key'] = api_key
        save_config(config)

    def generate_video(self, prompt, api_key, aspect_ratio, person_generation, 
                      duration_seconds, number_of_videos, negative_prompt="", 
                      seed=0, image=None):
        # Set random seed if provided
        if seed != 0:
            random.seed(seed)

        if api_key.strip():
            self.google_api_key = api_key
            self.save_google_api_key(api_key)
            
        if not self.google_api_key:
            error_message = "Google API key not found. Please provide a valid API key."
            print(error_message)
            return ("", "", error_message)
            
        try:
            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(5)

            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.google_api_key)

            config = types.GenerateVideosConfig(
                person_generation=person_generation,
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
                number_of_videos=number_of_videos
            )

            pbar.update_absolute(10)

            model = "veo-2.0-generate-001" 

            if image is not None:
                pil_image = tensor2pil(image)[0]

                operation = client.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    image=pil_image,
                    config=config,
                )
            else:
                operation = client.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    config=config,
                )

            pbar.update_absolute(20)

            while not operation.done:
                time.sleep(20)  
                operation = client.operations.get(operation)

                progress = min(70, 20 + int((time.time() % 50) / 50 * 50))  
                pbar.update_absolute(progress)
            
            # Check if operation completed successfully
            if hasattr(operation, 'error') and operation.error:
                error_message = f"Video generation failed: {operation.error.message}"
                print(error_message)
                return ("", "", error_message)

            pbar.update_absolute(90)
            
            if operation.response and operation.response.generated_videos:
                generated_video = operation.response.generated_videos[0]

                input_path = folder_paths.get_output_directory()
                video_filename = f"veo2_{str(uuid.uuid4())}.mp4"
                video_path = os.path.join(input_path, video_filename)

                generated_video.video.save(video_path)

                response_summary = {
                    "status": "success",
                    "prompt": prompt,
                    "model": model,
                    "aspect_ratio": aspect_ratio,
                    "duration": duration_seconds,
                    "seed": seed,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                }
                
                pbar.update_absolute(100)
                return (video_path, "", json.dumps(response_summary, indent=2))
            else:
                error_message = "No video was generated in the response"
                print(error_message)
                return ("", "", error_message)
                
        except Exception as e:
            error_message = f"Error generating video: {str(e)}"
            print(error_message)
            return ("", "", error_message)



NODE_CLASS_MAPPINGS = {
    "ComfyuiGoogleVeo2": ComfyuiGoogleVeo2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyuiGoogleVeo2": "Google Veo2 Video Generation",
}



