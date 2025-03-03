import telebot
from dotenv import load_dotenv
import os
from ollama import chat
from ollama import ChatResponse
# Загружаем переменные окружения
load_dotenv()

# Инициализируем бота
bot = telebot.TeleBot(os.getenv('TOKEN'))
# Обработчик команды /start
@bot.message_handler(commands=['start'])
def hello_message(message):
    bot.send_message(message.chat.id, 'Hello, I am a simple chatbot. Send me a message to start.')

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def answer_messages(message):
    response: ChatResponse = chat(model='phi4:latest', messages=[
    {
        'role': 'user',
        'content': message.text,
    },
    ])
    bot.send_message(message.chat.id, response['message']['content'])

# Запускаем бота
bot.infinity_polling()
