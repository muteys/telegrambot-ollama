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
    button1 = telebot.types.InlineKeyboardButton(text='Кнопка 1', callback_data='button1')
    button2 = telebot.types.InlineKeyboardButton(text='Кнопка 2', callback_data='button2')
    
    # Добавляем кнопки в клавиатуру
    markup.add(button1, button2)
    
    # Отправляем сообщение с inline-клавиатурой
    bot.send_message(message.chat.id, "Выберите кнопку:", reply_markup=markup)

# Обработчик inline-кнопок

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == 'button1':
        bot.send_message(call.message.chat.id, "Введите текс")
        user_data[chat_id] = 'waiting_for_input_1'
    elif call.data == 'button2':
        bot.send_message(call.message.chat.id, "Введите id")
        user_data[chat_id] = 'waiting_for_input_2'
        
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if user_data[chat_id] == 'waiting_for_input_1':
        bot.send_message(chat_id, 'Your request has been sent to the chatbot. Please wait for a response.')
        response: ChatResponse = chat(model='phi4:latest', messages=[
        {
            'role': 'user',
            'content': "На основе текста, что ты сейчас получишь, ты должен сгенерировать 3 вопроса, на которых можно дать развернутый ответ, помни, что твой ответ должен содержать только вопросы, так как его увидят ученики, которым ты их задаешшь, вот текст: " + message.text,
        },
        ])
        bot.send_message(message.chat.id, response['message']['content'])
        bot.send_message(message.chat.id, f'your id {create_room(message.text, response['message']['content'])}')
        del user_data[chat_id]
    elif user_data[chat_id] == 'waiting_for_input_2':
        result = find_room(message.text)
        if result != None:
            bot.send_message(message.chat.id, 'Текст задания')
            bot.send_message(message.chat.id, result[1])
            bot.send_message(message.chat.id, 'Задачи')
            bot.send_message(message.chat.id, result[2])
            del user_data[chat_id]
        else:
            bot.send_message(message.chat.id, 'Комната не найдена')
            del user_data[chat_id]
        

# Запускаем бота
bot.infinity_polling()
