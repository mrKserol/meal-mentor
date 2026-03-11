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
    Sends a POST request to the FastAPI service. Returns ingredients with weights
    and, if a nutrition dataset is configured, aggregated nutrition (calories,
    proteins, fats, carbohydrates).
    """
    try:
        payload = {"image_base64": image_base64}
        headers = {"Content-Type": "application/json"}
        raw_response = requests.post(SERVER_URL, json=payload, headers=headers)

        if raw_response.status_code != 200:
            st.error(f"Error: {raw_response.status_code}, {raw_response.text}")
            return None

        response = raw_response.json()
        if response.get("status") != "success":
            st.error(f"Unable to get result: {response.get('error', response)}")
            return None

        result = response.get("result")
        if isinstance(result, str):
            result = json.loads(result) if result else {}
        if not result:
            result = {}

        out = {"ingredients": result}
        if "nutrition" in response:
            out["nutrition"] = response["nutrition"]
        return out
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def plot_nutritional_info(nutritional_info):
    """Donut chart for calories and macros (proteins, fats, carbohydrates)."""
    n = nutritional_info
    if "proteins" not in n or "fats" not in n or "carbohydrates" not in n:
        return
    labels = "Proteins", "Fats", "Carbohydrates"
    sizes = [n["proteins"], n["fats"], n["carbohydrates"]]

    fig, ax = plt.subplots()
    fig.patch.set_alpha(0.0)

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda p: f"{p * sum(sizes) / 100:.0f}" if sum(sizes) else "0",
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
        0, 0,
        f'{n.get("calories", 0)}\nkcal',
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=20,
        color="white",
    )
    st.pyplot(fig, transparent=True)


st.title("Calorie Tracker")

st.config.set_option("server.maxUploadSize", 3)
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        img = Image.open(uploaded_file)
        st.image(img, use_column_width=True)

        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        data = get_nutritional_info(image_base64)
        if not data:
            st.stop()

        ingredients = data.get("ingredients") or {}
        if ingredients:
            st.subheader("Состав и вес (г)")
            for name, weight in ingredients.items():
                st.write(f"- **{name}**: {weight} г")
        else:
            st.info("На фото не обнаружено еды или не удалось определить состав.")

        nutrition = data.get("nutrition")
        if nutrition:
            plot_nutritional_info(nutrition)
        elif ingredients:
            st.caption(
                "Чтобы видеть калории и БЖУ, укажите путь к CSV с нутриентами "
                "(переменная NUTRITION_CSV_PATH) и перезапустите бэкенд."
            )
    except Exception as e:
        st.error(f"Error processing image: {e}")
