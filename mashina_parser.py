import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# Настройки
MAX_PAGES = 10 # сколько страниц парсим
DELAY = 1.5 # пауза между запросами
OUTPUT_FILE = "mashina_kg_cars.csv"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


# Функция загружает страницу и возвращает HTML
def get_html(session, url):
    try:
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  Ошибка при загрузке {url}: {e}")
        return None


# Функция определяет сколько всего страниц на сайте
def get_total_pages(soup):
    # Ищем кнопки пагинации с классом pagination_button
    buttons = soup.find_all("button", class_="pagination_button")
    max_page = 0
    for btn in buttons:
        text = btn.get_text(strip=True)
        if text.isdigit():
            num = int(text)
            if num > max_page:
                max_page = num
    return max_page


# Функция парсит одну карточку с машиной
def parse_card(card):
    data = {}

    # Ссылка на объявление
    href = card.get("href", "")
    data["url"] = "https://mashina.kg" + href

    # Название машины - внутри тега h3
    h3 = card.find("h3")
    if h3:
        data["title"] = h3.get_text(strip=True)
    else:
        data["title"] = ""

    # Город
    city_span = card.find("span", class_="text-white text-sm leading-5 truncate")
    if city_span:
        data["city"] = city_span.get_text(strip=True)
    else:
        data["city"] = ""

    # Ссылка на картинку
    img = card.find("img")
    if img:
        data["image_url"] = img.get("src", "")
    else:
        data["image_url"] = ""

    # Год и пробег в span где текст типа "2019/113413 km"
    year_mileage_span = card.find("span", class_="text-xs leading-4 whitespace-nowrap shrink-0")
    data["year"] = ""
    data["mileage_km"] = ""
    if year_mileage_span:
        text = year_mileage_span.get_text(strip=True)
        parts = text.split("/")
        if len(parts) == 2:
            data["year"] = parts[0].strip()
            # Убираем km или км и пробелы
            km_text = parts[1].replace("km", "").replace("км", "").strip()
            km_text = km_text.replace(" ", "")
            data["mileage_km"] = km_text

    # Цена в сомах 
    price_kgs_span = card.find("span", class_="font-bold text-xs leading-4 text-text-secondary whitespace-nowrap")
    data["price_kgs"] = ""
    if price_kgs_span:
        text = price_kgs_span.get_text(strip=True)
        # Убираем символ сома, неразрывные пробелы и обычные пробелы
        text = text.replace("⃀", "").replace("\xa0", "").replace(" ", "")
        if text.isdigit():
            data["price_kgs"] = text

    # Цена в долларахт там где есть знак $
    price_usd_spans = card.find_all("span", class_="text-xs leading-4 text-text-secondary whitespace-nowrap")
    data["price_usd"] = ""
    for span in price_usd_spans:
        text = span.get_text(strip=True)
        if "$" in text:
            text = text.replace("$", "").replace("\xa0", "").replace(" ", "")
            if text.isdigit():
                data["price_usd"] = text
                break

    # Двигатель и коробка передач
    # Ищем span где есть "л." и "/" 
    data["engine"] = ""
    data["transmission"] = ""
    all_spans = card.find_all("span")
    for span in all_spans:
        text = span.get_text(strip=True)
        if "л." in text and "/" in text:
            parts = text.split("/", 1)
            data["engine"] = parts[0].strip()
            data["transmission"] = parts[1].strip()
            break

    return data


# Функция парсит все карточки на странице
def parse_page(html):
    soup = BeautifulSoup(html, "lxml")
    # Ищем все ссылки которые начинаются с /details/
    cards = soup.find_all("a", href=re.compile(r"^/details/"))
    
    results = []
    for card in cards:
        car_data = parse_card(card)
        if car_data.get("url"):
            results.append(car_data)
    
    return results, soup


# Функция собирает объявления со всех страниц
def fetch_all_pages(session):
    all_cars = []
    seen_urls = set()  # чтобы не было дубликатов

    # Начинаем с первой страницы
    print("Парсим страницу 1...")
    html = get_html(session, "https://mashina.kg/search/passenger")
    if html is None:
        return all_cars

    page_cars, soup = parse_page(html)
    total_pages = get_total_pages(soup)
    print(f"  Всего страниц на сайте: {total_pages}")
    print(f"  Найдено машин на странице: {len(page_cars)}")

    # Добавляем первые машины
    for car in page_cars:
        if car["url"] not in seen_urls:
            seen_urls.add(car["url"])
            all_cars.append(car)

    if MAX_PAGES is not None:
        if MAX_PAGES < total_pages:
            pages_count = MAX_PAGES
        else:
            pages_count = total_pages
    else:
        pages_count = total_pages

    print(f"  Будем парсить страниц: {pages_count}")

    # Перебираем остальные страницы
    for page_num in range(2, pages_count + 1):
        print(f"Парсим страницу {page_num}...")
        
        time.sleep(DELAY)  # Ждем чтобы не нагружать сайт
        
        url = f"https://mashina.kg/search/passenger?page={page_num}"
        html = get_html(session, url)
        if html is None:
            continue

        page_cars, _ = parse_page(html)
        
        new_cars = 0
        for car in page_cars:
            if car["url"] not in seen_urls:
                seen_urls.add(car["url"])
                all_cars.append(car)
                new_cars += 1
        
        print(f"  Найдено: {len(page_cars)}, новых: {new_cars}")
        print(f"  Всего собрано: {len(all_cars)}")

    return all_cars


# Функция сохраняет данные в CSV
def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    column_order = ["url", "title", "price_usd", "price_kgs", "year", "mileage_km", "engine", "transmission", "city", "image_url"]
    # Берем только те колонки в которых есть данные
    column_order = [c for c in column_order if c in df.columns]
    df = df[column_order]
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\nГотово! Сохранено {len(df)} машин в файл: {filename}")


def main():
    print("=" * 50)
    print("ПАРСЕР mashina.kg")
    print("=" * 50)

    # Создаем сессию для запросов
    session = requests.Session()
    session.headers.update(HEADERS)

    # Собираем все объявления
    all_cars = fetch_all_pages(session)


    if all_cars:
        save_to_csv(all_cars, OUTPUT_FILE)
    else:
        print("Ничего не найдено :(")

    print("Программа завершена!")



if __name__ == "__main__":
    main()