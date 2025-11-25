from assistant_temp import LLMAssistant
from utils import image_url_to_base64


model_id = "80537f9eead1a5bfa72d5ac6ea6414379be41d4d4f6679fd776e9535d1eb58bb"

system_prompt = '''Оцени что на изображении.
Для изображений без еды - ответом должен быть пустой JSON-объект: {}
Для изображений, содержащих еду, в качестве ответа посчитай пищевую ценность.
Верни ответ в формате JSON с полями: calories, proteins, fats, carbohydrates
Возвращай только JSON, без лишнего текста.'''

assistant = LLMAssistant(system_prompt, model_id, temperature=0.01)

food_image_url = "https://images.unsplash.com/photo-1568901346375-23c9450c58cd"
food_image_Base64 = image_url_to_base64(food_image_url)

non_food_image_url = "https://images.unsplash.com/photo-1508356889337-11a080a10d06"
non_food_image_Base64 = image_url_to_base64(non_food_image_url)

food_response = assistant.generate_response(food_image_Base64, timeout=20)
print(f"Response for food image: {food_response}")

non_food_response = assistant.generate_response(non_food_image_Base64, timeout=20)
print(f"Response for non-food image: {non_food_response}")

### Output:
# Response for food image: {'status': 'success', 'result': {'calories': 500, 'proteins': 30, 'fats': 40, 'carbohydrates': 50}, 'error': ''}
# Response for non-food image: {'status': 'success', 'result': {}, 'error': ''}
