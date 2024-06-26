import threading
import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv

import lessons

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN')

bot = telebot.TeleBot(token)
active_polls = {}
user_votes = {}
poll_results = {}
poll_timers = {}
sent_results = set()  # Используется для отслеживания отправленных результатов
conn = sqlite3.connect('bot_users.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    is_admin BOOLEAN DEFAULT False,
    course INTEGER,
    group_number TEXT,
    faculty TEXT
)
''')

conn.commit()


def process_faculty_selection(message):
    faculty_mapping = {
        "ИТ": "ФИТ",
        "Юридический": "ЮФ",
        "Управление": "УФ",
        "Экономический": "ЭФ"
    }

    selected_faculty = message.text
    if selected_faculty == "Назад":
        handle_back(message)
    elif selected_faculty in faculty_mapping:
        faculty = faculty_mapping[selected_faculty]
        markup_course = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(4):
            button = types.KeyboardButton(str(i + 1))
            markup_course.add(button)
        bot.send_message(message.chat.id, "Для регистрации выберите свой курс:", reply_markup=markup_course)
        bot.register_next_step_handler(message, lambda m: process_course_step(m, faculty))
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите факультет с помощью кнопок.")
        bot.register_next_step_handler(message, process_faculty_selection)  # Повторная регистрация обработчика

def process_course_step(message, faculty):
    try:
        course = int(message.text)
        if 1 <= course <= 6:
            try:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                groups = lessons.get_group(faculty, course)
                for i in groups:
                    button = types.KeyboardButton(i)
                    markup.add(button)
                bot.send_message(message.chat.id, f"Курс {course} выбран. Теперь выберите номер группы:", reply_markup=markup)
                bot.register_next_step_handler(message, lambda m: process_group_step(m, course, faculty))
            except:
                bot.send_message(message.chat.id, "Выбор групп для данного курса пока не доступен, просьба ввести номер группы самостоятельно")
                bot.register_next_step_handler(message, lambda m: process_group_step(m, course, faculty))
        else:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер курса (от 1 до 6).")
            bot.register_next_step_handler(message, lambda m: process_course_step(m, faculty))  # Повторная регистрация обработчика
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер курса (целое число).")
        bot.register_next_step_handler(message, lambda m: process_course_step(m, faculty))  # Повторная регистрация обработчика
def process_group_step(message, course, faculty):
    group = message.text
    # Здесь добавьте логику для обработки выбранной группы
    bot.send_message(message.chat.id, f"Группа {group} на курсе {course} факультета {faculty} выбрана.")


def process_group_step(message, course, faculty):
    try:
        group = message.text
        if group and len(group) <= 14:
            add_user_to_db_with_course_group(message.chat.id, course, group, faculty)
            bot.send_message(message.chat.id, "Регистрация завершена. Спасибо!")
            handle_back(message)
        else:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер группы (до 14 символов).")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер группы.")


def add_user_to_db_with_course_group(chat_id, course, group, faculty):
    existing_user = get_user_info(chat_id)
    if existing_user:
        # User already exists, update the information
        cursor.execute('UPDATE users SET course=?, group_number=?, faculty=? WHERE chat_id=?',
                       (course, group, faculty, chat_id))
    else:
        # User doesn't exist, insert a new record
        cursor.execute('INSERT INTO users (chat_id, course, group_number, faculty) VALUES (?, ?, ?, ?)',
                       (chat_id, course, group, faculty))
    conn.commit()


def get_user_info(chat_id):
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    return cursor.fetchone()


@bot.message_handler(func=lambda message: message.text == "Назад")
def handle_back(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_schedule = types.KeyboardButton("Расписание")
    item_registration = types.KeyboardButton("Изменение данных")
    item_news_muiv = types.KeyboardButton("Новости МУИВа")
    item_news = types.KeyboardButton("Новости факультета")
    markup.add(item_schedule, item_registration, item_news, item_news_muiv)
    bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def handle_registration_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_it = types.KeyboardButton("ИТ")
    item_legal = types.KeyboardButton("Юридический")
    item_management = types.KeyboardButton("Управление")
    item_economics = types.KeyboardButton("Экономический")

    markup.add(item_it, item_legal, item_management, item_economics)

    bot.send_message(message.chat.id, "Привет!\nРад тебя тут видеть)\nЯ бот - помощник ВУЗа, через меня можно "
                                      "получать новости ВУЗа, а так же расписание занятий!\nПрошу пройди коротенькую "
                                      "регистрация:\nВыберите свой факультет:", reply_markup=markup)
    bot.register_next_step_handler(message, process_faculty_selection)


@bot.message_handler(commands=['admin'])
def set_admin(message):
    cursor.execute('''
        UPDATE users
        SET is_admin = 1
        WHERE chat_id = ?
        ''', (message.chat.id,))
    conn.commit()


@bot.message_handler(commands=['poll'])
def handle_create_poll(message):
    cursor.execute("SELECT is_admin FROM users WHERE chat_id = ?", (message.chat.id,))
    is_admin = cursor.fetchone()

    if is_admin and is_admin[0]:
        message_text = message.text[5:].strip()
        m_list = message_text.split('|')
        question = m_list[0].strip()
        options = m_list[1:-1]
        for i in range(len(options)):
            options[i] = options[i].strip()
        time_limit = int(m_list[-1])

        cursor.execute("SELECT chat_id FROM users")
        users = cursor.fetchall()
        for user in users:
            chat_id = user[0]
            poll_message = bot.send_poll(
                chat_id=chat_id,
                question=question,
                options=options,
                is_anonymous=False,  # или False, если опрос неанонимный
                allows_multiple_answers=False  # True, если допускается выбор нескольких вариантов
            )
            poll_id = poll_message.poll.id
            message_id = poll_message.message_id
            active_polls[poll_id] = {'chat_id': chat_id, 'message_id': message_id, 'question': question,
                                     'options': options}

            # Запуск таймера для завершения опроса через time_limit секунд
            poll_timers[poll_id] = threading.Timer(time_limit, end_poll, args=(poll_id,))
            poll_timers[poll_id].start()

    else:
        bot.send_message(message.chat.id, 'Вы не являетесь администратором и не можете создавать опросы.')


def end_poll(poll_id):
    if poll_id in active_polls:
        poll_data = active_polls[poll_id]
        chat_id = poll_data['chat_id']
        message_id = poll_data['message_id']
        question = poll_data['question']
        options = poll_data['options']
        bot.stop_poll(chat_id, message_id)

        # Подсчет результатов для текущего опроса
        results = [0] * len(options)
        if poll_id in user_votes:
            for votes in user_votes[poll_id].values():
                for vote in votes:
                    results[vote] += 1

        # Обновление общего результата голосования
        if question not in poll_results:
            poll_results[question] = {'results': [0] * len(options), 'options': options}
        for i in range(len(results)):
            poll_results[question]['results'][i] += results[i]

        del active_polls[poll_id]
        if poll_id in user_votes:
            del user_votes[poll_id]

        # Проверка на завершение всех опросов по данному вопросу
        if not any(p['question'] == question for p in active_polls.values()):
            if question not in sent_results:
                send_poll_results_to_all_users(question)
                sent_results.add(question)


def send_poll_results_to_all_users(question):
    results = poll_results[question]['results']
    options = poll_results[question]['options']
    result_message = f"Голосование завершено.\n\nВопрос: {question}\n"
    for i, option in enumerate(options):
        result_message += f"{option}: {results[i]} голосов\n"

    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()
    for user in users:
        chat_id = user[0]
        bot.send_message(chat_id, result_message)


@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    selected_options = poll_answer.option_ids

    if poll_id not in user_votes:
        user_votes[poll_id] = {}

    user_votes[poll_id][user_id] = selected_options



if __name__ == '__main__':
    bot.infinity_polling()
