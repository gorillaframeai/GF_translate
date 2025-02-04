import json
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

class GFDeepTranslateNode:
    """
    Node for translating text using Google Translate.
    Supports language selection from a list and automatic language detection.
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # Create a list of languages for selection (only language codes)
        language_list = list(GoogleTranslator().get_supported_languages(as_dict=True).keys())
        if 'en' not in language_list:
            language_list.append('en')  # Manually add 'en' if it is not present

        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Enter text"}),
                "src_lang": (language_list, {"default": "en"}),  # Source language
                "dest_lang": (language_list + ["none"], {"default": "en"}),  # Target language or "none"
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)
    FUNCTION = "translate_text"
    CATEGORY = "GF Tools"

    def translate_text(self, text, src_lang, dest_lang):
        """
        Translates text from one language to another.

        :param text: Text to translate.
        :param src_lang: Source language (e.g., 'ru' for Russian).
        :param dest_lang: Target language (e.g., 'en' for English) or "none".
        :return: Translated text.
        """
        if dest_lang == "none":
            return (text,)  # Return the original text if "none" is selected

        try:
            translation = GoogleTranslator(source=src_lang, target=dest_lang).translate(text)
            return (translation,)
        except Exception as e:
            return (f"Translation error: {e}",)

class GFJsonTranslate:
    @classmethod
    def INPUT_TYPES(cls):
        # Create a list of languages for selection (only language codes)
        language_list = list(GoogleTranslator().get_supported_languages(as_dict=True).keys())
        if 'en' not in language_list:
            language_list.append('en')  # Manually add 'en' if it is not present

        return {
            "required": {
                "input_path": ("STRING", {"default": ""}),  # Path to the input JSON file
                "source_lang": (language_list, {"default": "en"}),  # Source language
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

    def translate_texts(self, texts, source_lang, target_lang, max_workers=30):
        translated_texts = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_text = {executor.submit(self.translate_text, text, source_lang, target_lang): text for text in texts}
            for future in as_completed(future_to_text):
                translated_text = future.result()
                translated_texts.append(translated_text)
        return translated_texts

    def process_json(self, json_data, source_lang, target_lang, max_workers=30):
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
            print(f"File not found: {input_path}")
            return (None,)

        # Attempt to read the input JSON file with UTF-8 encoding
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
        except UnicodeDecodeError:
            print(f"Failed to decode file with UTF-8 encoding: {input_path}")
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

        print(f"Translated lines: {translated_count}")
        print(f"Translated JSON saved to {output_file_path}")
        return (output_file_path,)