import requests
from bs4 import BeautifulSoup
import json
import telebot
from telebot import types
import time

TELEGRAM_BOT_TOKEN = '6715496214:AAHm05j5GQAwdKX1lVWjLsHjC92LjvcGmNk'
TELEGRAM_BOT_ID = '-1002017716405'


class InternshipParser:
    def __init__(self, url, data_file="internships.json"):
        self.filename = 'internships.json'
        self.url = url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.data_file = data_file
        self.internships = self.load_internships()

    def get_soup(self, url):
        response = requests.get(url, headers=self.headers)
        return BeautifulSoup(response.content, 'html.parser')

    def load_internships(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as file:
                internships = json.load(file)
        except FileNotFoundError:
            internships = []
        return internships

    def save_internships(self):
        with open(self.data_file, 'w', encoding='utf-8') as file:
            json.dump(self.internships, file, indent=3, ensure_ascii=False)

    def extract_internship_data(self, internship):
        internship_dict = {}
        position_element = internship.find('span', {'class': 'serp-item__title'})
        if position_element:
            internship_dict['position'] = position_element.text.strip()
        else:
            internship_dict['position'] = None

        internship_id_element = internship.find('a', {'class': 'bloko-link'})
        if internship_id_element:
            href = internship_id_element['href']
            parts = href.split('/')
            internship_id = parts[-1].split('?')[0]
            internship_dict['internship_id'] = internship_id.strip()
        else:
            internship_dict['internship_id'] = None

        organization_name_element = internship.find('a', {'class': 'bloko-link bloko-link_kind-tertiary'})
        if organization_name_element:
            internship_dict['organisation_name'] = organization_name_element.text.strip().replace('\xa0', ' ')
        else:
            internship_dict['organisation_name'] = None

        type_elements = internship.find_all('span', {'class': 'label_light-violet--mfqJrKkFOboQUFsgaJp2'})
        if type_elements:
            for info in type_elements:
                info_text = info.text.strip()
                if 'Неполный рабочий день' in info_text:
                    internship_dict['type_elements'] = 'Неполный рабочий день'
                elif 'Полный рабочий день' in info_text:
                    internship_dict['type_elements'] = 'Полный рабочий день'
                else:
                    internship_dict['type_elements'] = 'Можно удаленно'
        else:
            internship_dict['type_elements'] = None

        salary_element = internship.find('span', {'class': 'bloko-header-section-2'})
        if salary_element:
            internship_dict['salary'] = salary_element.text.strip().replace('\u202f', '')
        else:
            internship_dict['salary'] = 'Не указано'

        return internship_dict

    def scrape_internships(self):
        soup = self.get_soup(self.url)
        internships = soup.find_all('div', class_='serp-item')

        for internship in internships:
            try:
                internship_data = self.extract_internship_data(internship)
            except Exception as e:
                print(f"Error notifying internship: {e}")
                continue

            internship_id = internship_data.get('internship_id')

            if internship_id and internship_id not in [item.get('internship_id') for item in self.internships]:
                self.internships.append(internship_data)

        self.save_internships()
        return self.internships


def send_internship(internship_data, chat_id, bot):
    message = format_internship_message(internship_data)

    # Создаем объект InlineKeyboardMarkup
    keyboard = types.InlineKeyboardMarkup()

    # Создаем кнопку с текстом "Смотреть" и ссылкой на сайт стажировки
    url_button = types.InlineKeyboardButton(text="Смотреть", url=f"https://hh.ru/vacancy/{internship_data['internship_id']}")

    # Добавляем кнопку в клавиатуру
    keyboard.add(url_button)

    # Отправляем сообщение с клавиатурой
    bot.send_message(chat_id, message, reply_markup=keyboard)


def format_internship_message(internship_data, escaping_markdown=True):
    position = internship_data.get('position', 'Не указана')
    organization_name = internship_data.get('organisation_name', 'Не указана')
    
    salary_types = {'unpaid': 'Неоплачиваемая', 'monthly': 'в месяц', 'hourly': 'в час'}
    salary = internship_data.get('salary', 'Не указана')
    if salary in salary_types:
        salary = salary_types[salary]
    
    type_elements = internship_data.get('type_elements')
    
    message = f"*{position}*\n" \
              f"Компания:  {organization_name}\n" \
              f"ЗП:  {salary}\n" \
              f"Тип:  {type_elements}\n\n"

    return message


def main():
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

    url = "https://hh.ru/search/vacancy?L_save_area=true&text=Senior&excluded_text=internship%2C+developer%2C+%D1%80%D0%B0%D0%B7%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D1%87%D0%B8%D0%BA%2C+%D1%81%D1%82%D0%B0%D0%B6%D0%B8%D1%80%D0%BE%D0%B2%D0%BA%D0%B0&professional_role=156&professional_role=160&professional_role=165&professional_role=96&professional_role=112&professional_role=113&professional_role=148&professional_role=114&professional_role=116&professional_role=124&professional_role=126&professional_role=10&professional_role=150&professional_role=121&salary=&currency_code=RUR&experience=doesNotMatter&schedule=fullDay&schedule=shift&schedule=flexible&schedule=remote&part_time=employment_project&part_time=employment_part&part_time=from_four_to_six_hours_in_a_day&part_time=only_saturday_and_sunday&part_time=start_after_sixteen&order_by=relevance&search_period=0&items_on_page=100"

    internship_scraper = InternshipParser(url)
    internships = internship_scraper.scrape_internships()

    for internship in internships:
        send_internship(internship, TELEGRAM_BOT_ID, bot)
        time.sleep(5)


if __name__ == "__main__":
    main()
    