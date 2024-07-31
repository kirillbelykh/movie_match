import csv
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

# Чтение данных из CSV файла
movies = []
with open("movies.csv", mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Пропуск заголовка
    for row in reader:
        movies.append({'title': row[0], 'image_url': row[1], 'trailer_url': row[2]})

# Хранилище данных для пользователей и групп
user_data = {}
group_data = {}
liked_movies = {}

# Инициализация бота
bot_token = "7206719443:AAGRZobSTm9zywTNLfj2hL7dQ8gmeCY0udY"
bot = telebot.TeleBot(bot_token)

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(chat_id=user_id, text="Привет! Чтобы начать, введите команду /register <название группы>.")

# Команда /register
@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.from_user.id
    group_name = message.text.split()[1] if len(message.text.split()) > 1 else None

    if not group_name:
        bot.send_message(chat_id=user_id, text="Пожалуйста, укажите название группы. Пример: /register family")
        return

    if group_name not in group_data:
        group_data[group_name] = {'members': set(), 'seen_movies': set(), 'current_movie': None, 'votes': {}}

    group_data[group_name]['members'].add(user_id)
    user_data[user_id] = {'group': group_name, 'liked': set(), 'disliked': set()}
    bot.send_message(chat_id=user_id, text=f"Вы зарегистрированы в группе {group_name}.")

    if len(group_data[group_name]['members']) >= 2:
        bot.send_message(chat_id=user_id, text=f"Теперь вы можете переписываться с другими участниками группы {group_name}.")
        for member_id in group_data[group_name]['members']:
            if member_id != user_id:
                bot.send_message(chat_id=member_id, text=f"Новый участник {message.from_user.username} присоединился к группе {group_name} и теперь вы можете переписываться.")
        send_random_movie(group_name)

# Обработка всех остальных сообщений
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id

    if user_id in user_data:
        group_name = user_data[user_id]['group']
        group_members = group_data[group_name]['members']
        text = message.text

        for member_id in group_members:
            if member_id != user_id:
                bot.send_message(member_id, f"{message.from_user.username}: {text}")
    else:
        bot.reply_to(message, "Вы не зарегистрированы в группе. Используйте /register для регистрации.")

# Команда /reset
@bot.message_handler(commands=['reset'])
def reset(message):
    user_id = message.from_user.id
    group_name = user_data.get(user_id, {}).get('group')

    if group_name:
        group_data[group_name]['members'].remove(user_id)
        user_data.pop(user_id, None)
        bot.send_message(chat_id=user_id, text="Вы вышли из группы.")
        for member_id in group_data[group_name]['members']:
            bot.send_message(chat_id=member_id, text=f"Пользователь {message.from_user.username} вышел из группы.")
    else:
        bot.send_message(chat_id=user_id, text="Вы не состоите ни в одной группе.")

# Отправка случайного фильма группе
def send_random_movie(group_name):
    available_movies = [movie for movie in movies if movie['title'] not in group_data[group_name]['seen_movies']]
    if not available_movies:
        for user_id in group_data[group_name]['members']:
            bot.send_message(chat_id=user_id, text="Все фильмы были просмотрены!")
        return

    movie = random.choice(available_movies)
    group_data[group_name]['current_movie'] = movie
    group_data[group_name]['seen_movies'].add(movie['title'])
    group_data[group_name]['votes'] = {user_id: None for user_id in group_data[group_name]['members']}

    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        InlineKeyboardButton("Лайк", callback_data='like'), 
        InlineKeyboardButton("Пропустить", callback_data='dislike'),
        InlineKeyboardButton("Трейлер", callback_data='trailer'), 
        InlineKeyboardButton("Сброс", callback_data='reset')
    )

    for user_id in group_data[group_name]['members']:
        bot.send_photo(chat_id=user_id, photo=movie['image_url'], caption=movie['title'].upper(), reply_markup=markup)


# Обработка нажатий кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id

    if user_id not in user_data:
        try:
            bot.answer_callback_query(callback_query_id=call.id, text="Вы не зарегистрированы.")
        except Exception as e:
            print(f"Error answering callback query: {e}")
        return

    group_name = user_data[user_id]['group']
    movie = group_data[group_name]['current_movie']

    if call.data == 'like':
        user_data[user_id]['liked'].add(movie['title'])
        if movie['title'] not in liked_movies:
            liked_movies[movie['title']] = set()
        liked_movies[movie['title']].add(user_id)
        group_data[group_name]['votes'][user_id] = 'like'
    elif call.data == 'dislike':
        user_data[user_id]['disliked'].add(movie['title'])
        group_data[group_name]['votes'][user_id] = 'dislike'
    elif call.data == 'trailer':
        bot.send_message(chat_id=user_id, text=f"Смотреть трейлер: {movie['trailer_url']}")
    elif call.data == 'reset':
        # Пользователь выходит из группы
        group_data[group_name]['members'].remove(user_id)
        user_data.pop(user_id, None)
        bot.send_message(chat_id=user_id, text="Вы вышли из группы.")
        for member_id in group_data[group_name]['members']:
            bot.send_message(chat_id=member_id, text=f"Пользователь {call.from_user.username} вышел из группы.")
        return

    try:
        bot.answer_callback_query(callback_query_id=call.id)
    except Exception as e:
        print(f"Error answering callback query: {e}")

    # Проверка, сделали ли все пользователи выбор
    if all(vote is not None for vote in group_data[group_name]['votes'].values()):
        # Проверка совпадения лайков у всех пользователей группы
        group_members = group_data[group_name]['members']
        if movie['title'] in liked_movies and all(uid in liked_movies[movie['title']] for uid in group_members):
            for uid in group_members:
                bot.send_message(chat_id=uid, text=f"Вы все лайкнули фильм: {movie['title']}")
            time.sleep(1)    
        send_random_movie(group_name)


# Запуск бота
bot.polling()
