import json
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator


class GFDeepTranslateNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # Создаем список языков для выбора (только коды языков)
        language_list = list(GoogleTranslator().get_supported_languages(as_dict=True).keys())
        if 'en' not in language_list:
            language_list.append('en')  # Вручную добавляем 'en', если его нет
        language_list.insert(0, "auto")  # Добавляем опцию автоопределения

        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Введите текст"}),
                "src_lang": (language_list, {"default": "auto"}),  # Автоопределение языка
                "dest_lang": (language_list, {"default": "en"}),  # Целевой язык
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)
    FUNCTION = "translate_text"
    CATEGORY = "GF Tools"

    def translate_text(self, text, src_lang, dest_lang):
        """
        Переводит текст с одного языка на другой.
        
        :param text: Текст для перевода.
        :param src_lang: Исходный язык (например, 'ru' для русского).
        :param dest_lang: Целевой язык (например, 'en' для английского).
        :return: Переведенный текст.
        """
        try:
            # Если выбран "auto", используем автоматическое определение языка
            if src_lang == "auto":
                translation = GoogleTranslator(source='auto', target=dest_lang).translate(text)
            else:
                translation = GoogleTranslator(source=src_lang, target=dest_lang).translate(text)

            return (translation,)
        except Exception as e:
            return (f"Ошибка при переводе: {e}",)

class GFJsonTranslate:
    @classmethod
    def INPUT_TYPES(cls):
        # Create a list of languages for selection (only language codes)
        language_list = list(GoogleTranslator().get_supported_languages(as_dict=True).keys())
        if 'en' not in language_list:
            language_list.append('en')  # Manually add 'en' if it is not present

        # Add 'auto' for automatic language detection
        language_list_with_auto = ['auto'] + language_list

        return {
            "required": {
                "input_path": ("STRING", {"default": ""}),  # Path to the input JSON file
                "source_lang": (language_list_with_auto, {"default": "auto"}),  # Source language with 'auto' option
                "target_lang": (language_list + ["none"], {"default": "en"}),  # Target language or "none"
                "fancy_mode": ("BOOLEAN", {"default": True}),  # Button to control structured output
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_json_path",)
    FUNCTION = "translate_json_file"
    CATEGORY = "Custom"

    def translate_text(self, text, source_lang, target_lang):
        if target_lang == "none":
            return text  # Return the original text if "none" is selected

        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
            return translated_text
        except Exception:
            return text  # Return the original text if translation fails

    def translate_texts(self, texts, source_lang, target_lang, max_workers=25):
        translated_texts = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_text = {executor.submit(self.translate_text, text, source_lang, target_lang): text for text in texts}
            for future in as_completed(future_to_text):
                translated_text = future.result()
                translated_texts.append(translated_text)
        return translated_texts

    def process_json(self, json_data, source_lang, target_lang, max_workers=25):
        paths_to_translate = []
        translated_texts = []  # Initialize translated_texts here

        def recursive_collect(data, path):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "title" and isinstance(value, str):
                        paths_to_translate.append((path + [key], value))
                    recursive_collect(value, path + [key])
            elif isinstance(data, list):
                for index, item in enumerate(data):
                    recursive_collect(item, path + [index])

        recursive_collect(json_data, [])

        if paths_to_translate:
            texts_to_translate = [text for _, text in paths_to_translate]
            translated_texts = self.translate_texts(texts_to_translate, source_lang, target_lang, max_workers)

            if len(translated_texts) != len(paths_to_translate):
                raise ValueError(f"The number of translated lines ({len(translated_texts)}) does not match the number of collected lines ({len(paths_to_translate)})")

            for (path, _), translated_text in zip(paths_to_translate, translated_texts):
                current = json_data
                for step in path[:-1]:
                    current = current[step]
                current[path[-1]] = translated_text

        return json_data, len(translated_texts)

    def translate_json_file(self, input_path, source_lang, target_lang, fancy_mode):
        # Check if the input file exists
        if not os.path.exists(input_path):
            return (None,)

        # Attempt to read the input JSON file with UTF-8 encoding
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
        except UnicodeDecodeError:
            return (None,)

        # Process JSON data
        processed_json_data, translated_count = self.process_json(json_data, source_lang, target_lang)

        # Create the directory if it does not exist
        output_dir = os.path.dirname(input_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write the translated JSON data to the output file
        output_file_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}-{target_lang}.json")
        with open(output_file_path, 'w', encoding='utf-8') as file:
            if fancy_mode:
                json.dump(processed_json_data, file, ensure_ascii=False, indent=4)
            else:
                json.dump(processed_json_data, file, ensure_ascii=False)

        return (output_file_path,)