# === Настройки ===
# Данные для отправки
phone_number = "+79101112233"  # Телефонный номер
name = "дядя Петя"              # Имя

# Путь к файлу с URL
file_path = r"C:\Users\ilya\Desktop\urls.txt"  # Укажите путь к вашему файлу

# Количество потоков
max_workers = 150  # Укажите количество потоков для многопоточной обработки
# === Конец блока настроек ===

# Импорты
import requests
from bs4 import BeautifulSoup
import idna
from urllib.parse import urlparse, urlunparse
import re
import concurrent.futures
import pandas as pd
from threading import Lock
import os

# Определяем тип файла на основе расширения
file_extension = os.path.splitext(file_path)[1].lower()
if file_extension == ".xlsx":
    file_type = "excel"
elif file_extension == ".txt":
    file_type = "txt"
else:
    print("Неизвестный формат файла. Поддерживаются только .xlsx и .txt.")
    exit()

# Функция для загрузки URL из Excel
def load_urls_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)  # Загружаем Excel файл
        urls = df['a'].dropna().tolist()  # Прочитать столбец 'a' и убрать пустые значения
        return urls
    except Exception as e:
        print(f"Ошибка при чтении Excel файла: {e}")
        return []

# Функция для загрузки URL из .txt
def load_urls_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = [line.strip() for line in file if line.strip()]  # Читаем строки и удаляем пустые
        return urls
    except Exception as e:
        print(f"Ошибка при чтении .txt файла: {e}")
        return []

# Загрузка URL из файла
if file_type == "excel":
    urls = load_urls_from_excel(file_path)
elif file_type == "txt":
    urls = load_urls_from_txt(file_path)
else:
    urls = []

if not urls:
    print("Список URL пуст. Проверьте файл или путь к нему.")
    exit()

# Удаление дубликатов из списка URL
initial_count = len(urls)
urls = list(dict.fromkeys(urls))
duplicates_removed = initial_count - len(urls)
print(f"Обнаружено уникальных URL: {len(urls)}")

# Переменные для подсчета статистики
total_sites = 0
successful_attempts = 0
lock = Lock()  # Потокобезопасная блокировка

# Функция для обработки каждого сайта
def process_site(url):
    global total_sites, successful_attempts

    url = url.strip()  # Убираем пробелы

    # Добавляем схему, если отсутствует
    if not url.startswith("http"):
        url = "https://" + url

    # Проверяем валидность URL
    try:
        parsed_url = urlparse(url)  # Разбираем URL
        domain = parsed_url.netloc or parsed_url.path  # Извлекаем домен (учитываем, если нет netloc)
        if "." not in domain:
            raise ValueError(f"Некорректный домен: {domain}")

        # Преобразуем кириллический домен в IDNA
        try:
            encoded_domain = idna.encode(domain).decode("utf-8")
        except idna.IDNAError as e:
            print(f"Ошибка кодировки домена {url}: {e}")
            return

        # Собираем новый URL с корректным доменом
        url = urlunparse((
            parsed_url.scheme,      # Протокол (http/https)
            encoded_domain,         # Домен в формате IDNA
            parsed_url.path,        # Путь
            parsed_url.params,      # Параметры
            parsed_url.query,       # Запросы
            parsed_url.fragment     # Фрагмент
        ))

    except Exception as e:
        print(f"Некорректный URL: {url}. Ошибка: {e}")
        return

    # Увеличиваем счетчик сайтов (с блокировкой)
    with lock:
        total_sites += 1

    try:
        # Пытаемся подключиться к сайту
        response = requests.get(url, timeout=10)
        print(f"Пытаемся получить сайт: {url}")
        print(f"Ответ от сервера: {response.status_code}")
        if response.status_code != 200:
            print(f"Не удалось получить страницу {url}. Код ошибки: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем форму
        form = soup.find('form')
        if not form:
            print(f"На сайте {url} форма не найдена.")
            return

        print(f"Форма найдена на сайте: {url}")

        # Подготавливаем данные для отправки
        data = {'phone': phone_number, 'name': name}

        # Определяем URL отправки формы
        submit_url = form.get('action') or url
        if not submit_url.startswith("http"):
            submit_url = url + submit_url

        response = requests.post(submit_url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"Заявка успешно отправлена на сайт {url}!")
            with lock:
                successful_attempts += 1
        else:
            print(f"Ошибка при отправке заявки на сайт {url}. Код ответа: {response.status_code}")

    except Exception as e:
        print(f"Ошибка при обработке сайта {url}: {e}")

# Многопоточная обработка
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    executor.map(process_site, urls)

# Вывод статистики
print(f"\nОбщее количество сайтов: {total_sites}")
print(f"Количество успешных отправленных заявок: {successful_attempts}")
if duplicates_removed > 0:
    print(f"Количество удалённых дублей: {duplicates_removed}")
if total_sites > 0:
    success_percentage = (successful_attempts / total_sites) * 100
    print(f"Процент успешных попыток: {success_percentage:.2f}%")
else:
    print("Не было попыток отправки заявок.")
