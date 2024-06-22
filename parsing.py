import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from pathlib import Path


months = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь",
              "декабрь"]

current_month_idx = datetime.now().month - 1
next_month_idx = (current_month_idx + 1) % 12

current_month = months[current_month_idx]
next_month = months[next_month_idx]

def extract_info(text):
    match = re.search(
        r'Расписание\s+(.*?)\s+(очная|заочная)\s+ф\.о\s+.*?\s+(январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)',
        text, re.IGNORECASE)
    if match:
        faculty, study_form, month = match.groups()
        if month.lower() == current_month or month.lower() == next_month:
            return faculty, study_form, month
    return None, None, None


def get_lessons():
    urls = [
        'https://www.muiv.ru/studentu/fakultet-upravleniya/raspisaniya/',
        'https://www.muiv.ru/studentu/fakultet-it/raspisaniya/',
        'https://www.muiv.ru/studentu/fakultet-ekonomiki-i-finansov/raspisaniya/',
        'https://www.muiv.ru/studentu/yuridicheskiy-fakultet/raspisaniya/'
    ]

    save_dir = Path('lessons')
    save_dir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        response = requests.get(url)
        webpage = response.content
        soup = BeautifulSoup(webpage, 'html.parser')
        for link in soup.find_all('a'):
            faculty, study_form, month = extract_info(link.text)
            if faculty and study_form and month:
                file_url = link.get('href')
                if not file_url.startswith('http'):
                    file_url = requests.compat.urljoin(url, file_url)
                file_name = f"{faculty} {study_form} {month} old.xls"
                file_path = save_dir / file_name
                response = requests.get(file_url)
                with open(file_path, 'wb') as f:
                    f.write(response.content)

if __name__ == '__main__':
    get_lessons()