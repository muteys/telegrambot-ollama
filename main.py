import telebot
from dotenv import load_dotenv
import os
import random
load_dotenv()
states = {}  # словарь для хранения состояний пользователей
bot = telebot.TeleBot(os.getenv('TOKEN'))
START = range(1)  # возможные состояния пользователя
@bot.message_handler(commands=['start'])
def hello_message(message):
    secret = 0
    states[secret] = START
    secret = random.randint(1,49494985894939494944)
    states[secret] = START
    id1 = message.from_user.id
    bot.send_message(message.chat.id, f'Ваш id {id1}')
bot.infinity_polling()