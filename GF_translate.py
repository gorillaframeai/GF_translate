import json
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

class GFDeepTranslateNode:
    """
    Нода для перевода текста с использованием Google Translate.
    Поддерживает выбор языков из списка и автоматическое определение языка.
    """
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
        # Создаем список языков для выбора (только коды языков)
        language_list = list(GoogleTranslator().get_supported_languages(as_dict=True).keys())
        if 'en' not in language_list:
            language_list.append('en')  # Вручную добавляем 'en', если его нет
        language_list.insert(0, "auto")  # Добавляем опцию автоопределения

        return {
            "required": {
                "input_path": ("STRING", {"default": ""}),  # Путь к входному JSON файлу
                "source_lang": (language_list, {"default": "auto"}),  # Автоопределение языка
                "target_lang": (language_list, {"default": "en"}),  # Целевой язык
                "pretty_print": ("BOOLEAN", {"default": True}),  # Кнопка для управления структурированным выводом
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_json_path",)
    FUNCTION = "translate_json_file"
    CATEGORY = "Custom"

    def is_chinese(self, text):
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return bool(chinese_pattern.search(text))

    def translate_text(self, text, source_lang, target_lang):
        try:
            # Если выбран "auto", используем автоматическое определение языка
            if source_lang == "auto":
                translator = GoogleTranslator(source='auto', target=target_lang)
            else:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
            print(f"Переведено: {text} -> {translated_text}")
            return translated_text
        except Exception as e:
            print(f"Ошибка при переводе: {e}")
            return text  # Возвращаем оригинальный текст, если перевод не удался

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

        def recursive_collect(data, path):
            if isinstance(data, dict):
                for key, value in data.items():
                    recursive_collect(value, path + [key])
            elif isinstance(data, list):
                for index, item in enumerate(data):
                    recursive_collect(item, path + [index])
            elif isinstance(data, str):
                if self.is_chinese(data):
                    paths_to_translate.append((path, data))

        recursive_collect(json_data, [])

        if paths_to_translate:
            texts_to_translate = [text for _, text in paths_to_translate]
            translated_texts = self.translate_texts(texts_to_translate, source_lang, target_lang, max_workers)

            if len(translated_texts) != len(paths_to_translate):
                raise ValueError(f"Количество переведенных строк ({len(translated_texts)}) не соответствует количеству собранных строк ({len(paths_to_translate)})")

            for (path, _), translated_text in zip(paths_to_translate, translated_texts):
                current = json_data
                for step in path[:-1]:
                    current = current[step]
                current[path[-1]] = translated_text

        return json_data

    def translate_json_file(self, input_path, source_lang, target_lang, pretty_print):
        # Читаем входной JSON файл
        with open(input_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        # Обрабатываем JSON данные
        processed_json_data = self.process_json(json_data, source_lang, target_lang)

        # Создаем директорию, если она не существует
        output_dir = os.path.dirname(input_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Записываем переведенные JSON данные в выходной файл
        output_file_path = os.path.join(output_dir, f"{os.path.basename(input_path)}-{target_lang}.json")
        with open(output_file_path, 'w', encoding='utf-8') as file:
            if pretty_print:
                json.dump(processed_json_data, file, ensure_ascii=False, indent=4)
            else:
                json.dump(processed_json_data, file, ensure_ascii=False)

        print(f"Переведенный JSON сохранен в {output_file_path}")
        return (output_file_path,)