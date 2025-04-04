import telebot
import os
import re
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID_TO_FORWARD = os.environ.get("CHAT_ID_TO_FORWARD")
if CHAT_ID_TO_FORWARD:
    CHAT_ID_TO_FORWARD = str(CHAT_ID_TO_FORWARD)

ALLOWED_USERNAMES_STR = os.environ.get("ALLOWED_USERNAMES", "")
ALLOWED_USERNAMES = [username.lower() for username in ALLOWED_USERNAMES_STR.split(",")]

ALLOWED_CHAT_TYPES = ['private']

bot = telebot.TeleBot(BOT_TOKEN)

user_ratings = {}
user_reviews = {}
accepted_helps = {}

def get_user_rating(username):
    return user_ratings.get(username, 0)

def add_review(username, review_text, rating):
    if username not in user_reviews:
        user_reviews[username] = []
    user_reviews[username].append({"text": review_text, "rating": rating})

def rating_to_stars(rating):
    if rating == 0:
        return "нет"
    return "⭐" * rating

def is_allowed_user(username):
    return username.lower() in ALLOWED_USERNAMES

def is_allowed_chat(chat_type):
    return chat_type in ALLOWED_CHAT_TYPES

def validate_phone(phone):
    phone = re.sub(r"\D", "", phone)
    if not phone.startswith(('7', '8')):
        return "Номер телефона должен начинаться с 7 или 8."
    if not phone.isdigit():
        return "Номер телефона должен состоять только из цифр."
    return None

def validate_dates(dates):
    match = re.match(r"(\d{2}\.\d{2}\.\d{4}) - (\d{2}\.\d{2}\.\d{4})", dates)
    if not match:
        return "Пожалуйста, введите сроки пребывания в формате: ДД.ММ.ГГГГ - ДД.ММ.ГГГГ"
    try:
        date1 = datetime.strptime(match.group(1), "%d.%m.%Y")
        date2 = datetime.strptime(match.group(2), "%d.%m.%Y")
        if date1 > date2:
            return "Первая дата не может быть позже второй."
    except ValueError:
        return "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ"
    return None

def validate_fio(fio):
    parts = fio.split()
    if len(parts) != 3:
        return "Пожалуйста, введите ФИО в формате: Фамилия Имя Отчество"
    return None

@bot.message_handler(commands=['start'])
def start(message):
    if not is_allowed_chat(message.chat.type):
        bot.reply_to(message, "Заполнение анкеты разрешено только в личных сообщениях с ботом.")
        return

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = telebot.types.KeyboardButton("📝 Отправить анкету")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Привет! Нажмите кнопку, чтобы отправить анкету.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "📝 Отправить анкету")
def send_form(message):
    if not is_allowed_chat(message.chat.type):
        bot.reply_to(message, "Заполнение анкеты разрешено только в личных сообщениях с ботом.")
        return

    user = message.from_user
    if user.username is None:
        bot.send_message(message.chat.id, "У вас не установлен username в Telegram. Пожалуйста, укажите ваш username (начинающийся с @):")
        bot.register_next_step_handler(message, get_custom_username)
    else:
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество):")
        bot.register_next_step_handler(msg, get_full_name)

def get_custom_username(message):
    username = message.text
    if not username.startswith('@'):
        bot.send_message(message.chat.id, "Username должен начинаться с @. Пожалуйста, укажите ваш username:")
        bot.register_next_step_handler(message, get_custom_username)
        return

    user_ratings[message.from_user.id] = {'custom_username': username}
    msg = bot.send_message(message.chat.id, "Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество):")
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    fio = message.text
    error_message = validate_fio(fio)
    if error_message:
        bot.send_message(message.chat.id, error_message)
        bot.register_next_step_handler(message, get_full_name)
        return

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    finalist_button = telebot.types.KeyboardButton("Финалист")
    semifinalist_button = telebot.types.KeyboardButton("Полуфиналист")
    winner_button = telebot.types.KeyboardButton("Победитель")
    keyboard.add(finalist_button, semifinalist_button, winner_button)

    msg = bot.send_message(message.chat.id, "Укажите ваш статус участника:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, get_status, full_name=fio)

def get_status(message, full_name):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    season1 = telebot.types.KeyboardButton("1")
    season2 = telebot.types.KeyboardButton("2")
    season3 = telebot.types.KeyboardButton("3")
    season4 = telebot.types.KeyboardButton("4")
    season5 = telebot.types.KeyboardButton("5")
    keyboard.add(season1, season2, season3, season4, season5)

    msg = bot.send_message(message.chat.id, "Укажите номер сезона участия (от 1 до 5):", reply_markup=keyboard)
    bot.register_next_step_handler(msg, get_season, full_name=full_name, status=message.text)

def get_season(message, full_name, status):
    msg = bot.send_message(message.chat.id, "Укажите ваш контактный телефон (пример: 79141234567):", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, get_phone, full_name=full_name, status=status, season=message.text)

def get_phone(message, full_name, status, season):
    phone = message.text
    error_message = validate_phone(phone)
    if error_message:
        bot.send_message(message.chat.id, error_message)
        bot.register_next_step_handler(message, get_phone, full_name=full_name, status=status, season=season)
        return

    msg = bot.send_message(message.chat.id, "Укажите сроки пребывания в столице (пример: 01.01.2024 - 15.01.2024):")
    bot.register_next_step_handler(msg, get_dates, full_name=full_name, status=status, season=season, phone=phone)

def get_dates(message, full_name, status, season, phone):
    dates = message.text
    error_message = validate_dates(dates)
    if error_message:
        bot.send_message(message.chat.id, error_message)
        bot.register_next_step_handler(message, get_dates, full_name=full_name, status=status, season=season, phone=phone)
        return

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    meeting_button = telebot.types.KeyboardButton("Встреча")
    logistics_button = telebot.types.KeyboardButton("Гостиницы")
    hotel_button = telebot.types.KeyboardButton("Гостиницы")
    routes_button = telebot.types.KeyboardButton("Маршруты")
    culture_button = telebot.types.KeyboardButton("Культурная программа")
    own_button = telebot.types.KeyboardButton("Своё")
    keyboard.add(meeting_button, logistics_button, hotel_button, routes_button, culture_button, own_button)
    msg = bot.send_message(message.chat.id, "Выберите тип запроса или укажите свой:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, get_request, full_name=full_name, status=status, season=season, phone=phone, dates=dates, user_id=message.from_user.id)

def get_request(message, full_name, status, season, phone, dates, user_id):
    user_info = bot.get_chat(user_id)
    username = user_info.username
    if username is None:
        username = user_ratings.get(user_id, {}).get('custom_username')
    form_text = (
        "<b>Новая анкета:</b>\n\n"
        f"ФИО: {full_name}\n"
        f"Статус участника: {status}\n"
        f"Сезон участия: {season}\n"
        f"Телефон: {phone}\n"
        f"Сроки пребывания: {dates}\n"
        f"Запрос: {message.text}\n"
        f"ID Пользователя: {user_id}\n"
    )

    keyboard = telebot.types.InlineKeyboardMarkup()
    button_help = telebot.types.InlineKeyboardButton(text="✅ Помочь", callback_data=f"help_{user_id}")
    button_partly_help = telebot.types.InlineKeyboardButton(text="❓ Отчасти готов помочь", callback_data=f"partly_help_{user_id}")
    keyboard.add(button_help, button_partly_help)

    try:
        bot.send_message(CHAT_ID_TO_FORWARD, form_text, parse_mode="HTML", reply_markup=keyboard)
        bot.send_message(message.chat.id, "Спасибо! Ваша анкета отправлена на рассмотрение.", reply_markup=telebot.types.ReplyKeyboardRemove())
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при отправке анкеты: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    username = call.from_user.username
    action, user_id = call.data.split('_')
    user_id = int(user_id)

    if action == "help" or action == "partly_help":
        if not is_allowed_user(username):
            bot.answer_callback_query(call.id, "У вас нет прав для отклика на анкеты.")
            return

        respondent_username = call.from_user.username
        respondent_rating = get_user_rating(respondent_username)
        stars = rating_to_stars(respondent_rating)

        keyboard = telebot.types.InlineKeyboardMarkup()
        accept_button = telebot.types.InlineKeyboardButton(text="✅ Принять помощь", callback_data=f"accept_{action}_{respondent_username}_{user_id}")
        keyboard.add(accept_button)

        notification_text = (
            f"На вашу анкету откликнулся дежурный!\n"
            f"Его рейтинг: {stars}\n"
            f"Он {'готов помочь' if action == 'help' else 'отчасти готов помочь'}.  Принять помощь?"
        )
        try:
            bot.send_message(user_id, notification_text, reply_markup=keyboard)
            bot.answer_callback_query(call.id, "Вы откликнулись на анкету. Ожидайте ответа пользователя.")

        except Exception as e:
            print(f"Ошибка при отправке уведомления: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при отправке уведомления пользователю.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
def handle_accept_decline(call):
    try:
        data = call.data.split('_')
        action = data[0]
        help_type = data[1]
        respondent_username = data[2]
        user_id = int(data[3])

        respondent_rating = get_user_rating(respondent_username)

        try:
            user_info = bot.get_chat(user_id)
            requester_username = user_info.username
            requester_username_tg = user_info.username if user_info.username else 'не указан' #Получаем username, если он есть
        except Exception as e:
            print(f"Не удалось получить username пользователя: {e}")
            requester_username = "Не удалось получить username"
            requester_username_tg = 'не удалось получить'

        accept_text = (f"Пользователь @{requester_username} принял вашу помощь ({'полную' if help_type == 'help' else 'частичную'}).  "
                       f"Вы можете связаться с ним для уточнения деталей.")
        keyboard = telebot.types.InlineKeyboardMarkup()
        finish_button = telebot.types.InlineKeyboardButton(text="✅ Закончить", callback_data=f"finish_{respondent_username}_{user_id}")
        keyboard.add(finish_button)

        try:
            accepted_helps[user_id] = respondent_username
            bot.send_message(bot.get_chat(username=respondent_username).id,
                             f"На Ваше предложение помощи согласились! Telegram для связи: @{requester_username_tg}",
                             reply_markup=keyboard)
            bot.answer_callback_query(call.id, "Вы приняли помощь. Контакты пользователя отправлены помощнику.")
            bot.send_message(user_id, "Вы успешно приняли, ожидайте пока с вами свяжутся")

        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
            bot.answer_callback_query(call.id, "Произошла ошибка при отправке сообщения.")

    except Exception as e:
        print(f"Error in handle_accept_decline: {e}  call.data = {call.data}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("finish_"))
def handle_finish(call):
    try:
        data = call.data.split('_')
        respondent_username = data[1]
        user_id = int(data[2])
        bot.send_message(user_id, f"Пожалуйста, оставьте отзыв о @{respondent_username}:")
        bot.register_next_step_handler(call.message, get_review, respondent_username=respondent_username, user_id=user_id)
    except Exception as e:
        print(f"Error in handle_finish: {e}")

def get_review(message, respondent_username, user_id):
    review_text = message.text
    keyboard = telebot.types.InlineKeyboardMarkup()
    button1 = telebot.types.InlineKeyboardButton(text="1", callback_data=f"review_1_{respondent_username}")
    button2 = telebot.types.InlineKeyboardButton(text="2", callback_data=f"review_2_{respondent_username}")
    button3 = telebot.types.InlineKeyboardButton(text="3", callback_data=f"review_3_{respondent_username}")
    button4 = telebot.types.InlineKeyboardButton(text="4", callback_data=f"review_4_{respondent_username}")
    button5 = telebot.types.InlineKeyboardButton(text="5", callback_data=f"review_5_{respondent_username}")
    keyboard.add(button1, button2, button3, button4, button5)
    bot.send_message(message.chat.id, "Пожалуйста, оцените помощь от 1 до 5:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("review_"))
def handle_review_rating(call):
    rating = int(call.data.split('_')[1])
    respondent_username = call.data.split('_')[2]
    add_review(respondent_username, call.message.text, rating)
    bot.send_message(call.message.chat.id, "Спасибо за ваш отзыв!")

def handler(event, context):
    try:
        bot.process_new_updates([telebot.types.Update.de_json(event['body'])])
        return {
            'statusCode': 200,
            'body': 'ok',
        }
    except Exception as e:
        print(f"Ошибка в handler: {e}")
        return {
            'statusCode': 500,
            'body': f"Error: {e}"
        }

if __name__ == '__main__':
    print("Бот запущен локально.  Для остановки нажмите Ctrl+C")
    bot.infinity_polling()