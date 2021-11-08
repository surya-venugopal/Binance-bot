import requests
import time

# list of quotes
quotes = [
    'First, solve the problem. Then, write the code. – John Johnson',
    'Experience is the name everyone gives to their mistakes. – Oscar Wilde',
    'Code is like humor. When you have to explain it, it’s bad. – Cory House',
    'Before software can be reusable it first has to be usable. – Ralph Johnson',
    'Optimism is an occupational hazard of programming: feedback is the treatment. - Kent Beck'
]


# chat id of bot : 527450766
# loop through the quotes
for quote in quotes:
    url = 'https://api.telegram.org/bot2072407643:AAEq8g8QuQe13WY1n9lhTKh5AWQNClu0w48/sendMessage?chat_id=-1001590033171&text={}'.format(quote)
    requests.get(url)
    print('hi')
    # sends new quotes every 20seconds
    time.sleep(20)


# from telegram import Update
# from telegram.ext import Updater, CommandHandler, CallbackContext


# telegram_bot_token = "2072407643:AAEq8g8QuQe13WY1n9lhTKh5AWQNClu0w48"

# updater = Updater(token=telegram_bot_token, use_context=True)
# dispatcher = updater.dispatcher

# def random(update, context):
#     # fetch data from the api
#     response = requests.get('http://quotes.stormconsultancy.co.uk/random.json')
#     data = response.json()
#     # send message
#     context.bot.send_message(chat_id=update.effective_chat.id, text=data['quote']) 

# # linking the /random command with the function random() 
# quotes_handler = CommandHandler('random', random)
# dispatcher.add_handler(quotes_handler)
# # updater.start_polling()
# # updater.idle()
