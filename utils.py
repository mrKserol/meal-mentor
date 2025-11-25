# import base64
# import requests
#
#
# def image_url_to_base64(image_url: str) -> str:
#     response = requests.get(image_url)
#     image_bytes = response.content
#     return base64.b64encode(image_bytes).decode("utf-8")

import requests
import base64

def image_url_to_base64(image_url, timeout=10):
    """
    Convert image from URL to base64 string (without data URL prefix)
    """
    try:
        response = requests.get(image_url, timeout=timeout)
        response.raise_for_status()

        # Encode to base64 WITHOUT data URL prefix
        image_base64 = base64.b64encode(response.content).decode('utf-8')
        return image_base64

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None