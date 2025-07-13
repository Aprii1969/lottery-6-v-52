import json
import os

def load_json_config(filepath):
    """
    Загружает JSON-конфигурацию из файла.
    Возвращает пустой dict, если файл не существует, пуст или содержит некорректный JSON.
    """
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {filepath}: {e}. Returning empty dict.")
    except Exception as e:
        print(f"ERROR: Problem reading {filepath}: {e}. Returning empty dict.")
    return {}

def save_json_config(filepath, data):
    """
    Сохраняет словарь в JSON-файл. Создает директории, если необходимо.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save config to {filepath}: {e}")
        return False