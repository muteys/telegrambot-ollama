import telebot
from dotenv import load_dotenv
import os
from ollama import chat
from ollama import ChatResponse
import sqlite3
from random import randint
# Загружаем переменные окружения
load_dotenv()
user_data = {}
rooms_data = {}

def get_id():
    id = str(randint(100000,999999))
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE id=?", (id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return get_id()  # Recursively call the function until a unique ID is generated
    else:
        return id

def save_answers(id, message):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE id=?", (id,))
    result = cursor.fetchone()
    bot.send_message(message.chat.id, 'Ваш ответ проверяется, это может занять несколько минут...')
    response: ChatResponse = chat(model='phi4:latest', messages=[
    {
        'role': 'user',
        'content': "На основе текста, что ты сейчас получишь, и 3 вопросов, на которых можно дать развернутый ответ, ты должен оценить ответы ученика и дать оценку от 0 до 2 баллов, твой ответ должен содержать только баллы за ответы отделенных пробелами, так как они будут заноситься в базу данных в таком виде: 1 0 2, вот текст: " + result[1]+", вот вопросы: "+ result[2]+', вот ответы ученика: '+message.text,
    },
    ])
    cursor.execute('''CREATE TABLE IF NOT EXISTS answers
                         (id text PRIMARY KEY,
                          name text,
                          marks text)''')
    cursor.execute("INSERT INTO answers VALUES (?,?,?)", (id,f'{message.from_user.first_name} {message.from_user.last_name}', response['message']['content']))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, 'Ваши ответы проверены.')

def create_room(message_text, response_text):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms
                         (id text PRIMARY KEY,
                          request text,
                          response text)''')
    room_id = get_id()
    cursor.execute("INSERT INTO rooms VALUES (?,?,?)", (room_id, message_text, response_text))
    conn.commit()
    conn.close()
    print(f'Room {room_id} created')
    return room_id    

def delete_room(room_id):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    cursor.execute("DELETE FROM answers WHERE id=?", (room_id,))
    conn.commit()
    conn.close()
    print(f'Room {room_id} deleted')

def find_marks(id):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM answers WHERE id=?", (id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result
    else:
        return None

def find_room(room_id):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE id=?", (room_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result
    else:
        return None

# Инициализируем бота
bot = telebot.TeleBot(os.getenv('TOKEN'))
# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаем inline-клавиатуру
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Создаем две inline-кнопки
    button1 = telebot.types.InlineKeyboardButton(text='Учитель', callback_data='Teacher|')
    button2 = telebot.types.InlineKeyboardButton(text='Ученик', callback_data='Student|')
    
    # Добавляем кнопки в клавиатуру
    markup.add(button1, button2)
    
    # Отправляем сообщение с inline-клавиатурой
    bot.send_message(message.chat.id, "Выберите кнопку:", reply_markup=markup)
# Обработчик inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    action, additional_info = call.data.split('|')
    if action == 'Teacher':
        bot.send_message(chat_id, "Введите текс, на основе которого будут генерироваться вопросы")
        user_data[chat_id] = 'waiting_for_input_1'
    elif action == 'Student':
        bot.send_message(chat_id, "Введите id полученое от учителя")
        user_data[chat_id] = 'waiting_for_input_2'
    elif action == 'Check_marks':
        results = find_marks(additional_info)
        if results != None:
            bot.send_message(chat_id, f'{results[1]} {results[2]}')
        else:
            bot.send_message(chat_id, 'Пока никто не выполнил задания')
        markup = telebot.types.InlineKeyboardMarkup()
        button_update = telebot.types.InlineKeyboardButton(text='Обновить информацию', callback_data=f'Check_marks|{additional_info}')
        button_delete = telebot.types.InlineKeyboardButton(text='Окончить сессию', callback_data=f'Delete_room|{additional_info}')
        markup.add(button_update, button_delete)
        bot.send_message(chat_id, "Нажмите кнопку для обновления информации или для окончания ссесии:", reply_markup=markup)
    elif action == 'Delete_room':
        delete_room(additional_info)
        bot.send_message(chat_id, 'Сессия окончена')
        del user_data[chat_id]
        
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if user_data[chat_id] == 'waiting_for_input_1':
        bot.send_message(chat_id, 'Ваш текст обрабатывается, это может занять несколько минут...')
        user_data[chat_id] = 'waiting'
        response: ChatResponse = chat(model='phi4:latest', messages=[
        {
            'role': 'user',
            'content': "На основе текста, что ты сейчас получишь, ты должен сгенерировать 3 вопроса, на которых можно дать развернутый ответ, помни, что твой ответ должен содержать только вопросы, так как его увидят ученики, которым ты их задаешшь, вот текст: " + message.text,
        },
        ])
        bot.send_message(chat_id, response['message']['content'])
        room_id = create_room(message.text, response['message']['content'])
        bot.send_message(message.chat.id, f'Ваш личный id {room_id}, передайте его ученикам')
        user_data[chat_id] = "waiting_for_start"
        markup = telebot.types.InlineKeyboardMarkup()
    
        # Создаем две inline-кнопки
        button1 = telebot.types.InlineKeyboardButton(text='Оценки', callback_data=f'Check_marks|{room_id}')
        
        # Добавляем кнопки в клавиатуру
        markup.add(button1)
        
        # Отправляем сообщение с inline-клавиатурой
        bot.send_message(chat_id, "Нажмите кнопку для вывода оценок:", reply_markup=markup)
    elif user_data[chat_id] == 'waiting_for_input_2':
        rooms_data[chat_id] = message.text
        result = find_room(rooms_data[chat_id])
        if result != None:
            bot.send_message(chat_id, 'Текст задания')
            bot.send_message(chat_id, result[1])
            bot.send_message(chat_id, 'Задачи')
            bot.send_message(chat_id, result[2])
            bot.send_message(chat_id, 'Ответы писать одним сообщением отделяя их номером 1. или 1)')
            user_data[chat_id] = 'waiting_for_answers'
        else:
            bot.send_message(chat_id, 'Комната не найдена')
            user_data[chat_id] = "waiting_for_start"
    elif user_data[chat_id] == 'waiting_for_answers':
        user_data[chat_id] = 'waiting'
        save_answers(rooms_data[chat_id], message)
        user_data[chat_id] = 'waiting_for_start'
    elif user_data[chat_id] == "waiting":
        bot.send_message(chat_id, 'Пожалуйста подождите')
    elif user_data[chat_id] == "waiting_for_start":
        bot.send_message(chat_id,"Пожалуйста введите команду /start")

# Запускаем бота
bot.infinity_polling()
