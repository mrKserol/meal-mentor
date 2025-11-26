import requests
import streamlit as st
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import base64
import json

SERVER_URL = "http://127.0.0.1:8000/generate_response"


def get_nutritional_info(image_base64: str):
    """
    Sends a POST request to the FastAPI service to retrieve nutritional information
    for a given base64 encoded image.

    Args:
        image_base64 (str): The base64 encoded image string.

    Returns:
        dict or None: A dictionary containing nutritional information with the keys
        'calories', 'proteins', 'fats', and 'carbohydrates' if the request is
        successful. Returns None if there is an error or if the nutritional information
        is not available.
    """
    try:
        # Prepare payload and headers for the request
        payload = {"image_base64": image_base64}
        headers = {"Content-Type": "application/json"}

        # Send POST request
        raw_response = requests.post(SERVER_URL, json=payload, headers=headers)

        # Handle response
        if raw_response.status_code == 200:
            response = raw_response.json()

            if response["status"] == "success":
                result = response["result"]

                if isinstance(result, str):
                    result = json.loads(response["result"])

                if result:
                    return result
                else:
                    st.warning("Nutritional information not available for this image.")
                    return None
            else:
                st.error(f"Unable to retrieve nutritional information: {response}.")
                return None
        else:
            st.error(f"Error: {raw_response.status_code}, {raw_response.text}")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def plot_nutritional_info(nutritional_info):
    """Function to plot a donut chart with nutritional information."""
    labels = "Proteins", "Fats", "Carbohydrates"
    sizes = [
        nutritional_info["proteins"],
        nutritional_info["fats"],
        nutritional_info["carbohydrates"],
    ]

    fig, ax = plt.subplots()
    fig.patch.set_alpha(0.0)

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda p: f"{p * sum(sizes) / 100:.0f}",
        startangle=90,
        wedgeprops={"width": 0.5},
    )

    ax.axis("equal")

    for text in texts:
        text.set_color("white")

    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(16)
        x, y = autotext.get_position()
        autotext.set_position((x * 1.2, y * 1.2))

    plt.text(
        0,
        0,
        f'{nutritional_info["calories"]}\nkcal',
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=20,
        color="white",
    )

    st.pyplot(fig, transparent=True)


# Streamlit app
st.title("Calorie Tracker")

# File uploader for image
st.config.set_option("server.maxUploadSize", 3)
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        # Display uploaded image
        img = Image.open(uploaded_file)
        st.image(img, use_column_width=True)

        # Convert image to Base64
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Send Base64-encoded image to FastAPI
        nutritional_info = get_nutritional_info(image_base64)

        if nutritional_info:
            plot_nutritional_info(nutritional_info)
    except Exception as e:
        st.error(f"Error processing image: {e}")
