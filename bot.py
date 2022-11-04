import telebot
from telebot import types
import parse
import os


bot = telebot.TeleBot(os.environ['LIQUIPARSER_TOKEN'])
hide_board = types.ReplyKeyboardRemove()
eventPool = ["The International 2022", "Shanghai Major"]
choosed = dict()
dota_event = None

#Commands handlers
@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(m.chat.id, "Hello! I will help you to get parsed matches for a tournament from Liquipedia")
    handle_event_choice(m)

@bot.message_handler(commands=["viewEvent"])
def view_event(m):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if choosed:
        for i in choosed:
            item = types.KeyboardButton(i)
            markup.add(item)
        message = bot.send_message(m.chat.id, "Which event do you want to view?", reply_markup=markup)
        bot.register_next_step_handler(message, handle_team_view)
    else:
        bot.send_message(m.chat.id, "There are no configured event patterns")

@bot.message_handler(commands=["reset"])
def reset_event(m):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for i in choosed:
        item = types.KeyboardButton(i)
        markup.add(item)
    message = bot.send_message(m.chat.id, 'Choose an event to reset find pattern', reply_markup=markup)
    bot.register_next_step_handler(message, handle_team_reset)

@bot.message_handler(commands=["showMatches"])
def show_matches(m):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if choosed:
        for i in choosed:
            item = types.KeyboardButton(i)
            markup.add(item)
        message = bot.send_message(m.chat.id, "For which event do you want to show matches based on your pattern?", reply_markup=markup)
        bot.register_next_step_handler(message, handle_event_matches)
#Commands handlers

def handle_event_matches(m):
    choosed_teams = choosed[m.text]
    global dota_event
    if dota_event is not None:
        if isinstance(dota_event, parse.DotaEvent):
            match_list = dota_event.get_filtered_matches(choosed_teams)
    temp_str = ''
    for match in match_list:
        temp_str += f'{match}\n'
    bot.send_message(m.chat.id, temp_str)

def handle_team_reset(m):
    choosed.pop(m.text)
    bot.send_message(m.chat.id, f"{m.text} was successfully removed from your choosed events")

def handle_team_view(m):
    if m.text in choosed:
        temp_str = ', '.join(i for i in choosed[m.text])
        bot.send_message(m.chat.id, temp_str)

def handle_event_choice(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
    for i in range(len(eventPool)):
        item = types.KeyboardButton(eventPool[i])
        markup.add(item)
    message = bot.send_message(m.chat.id,"Please choose a tournament:",reply_markup=markup)
    bot.register_next_step_handler(message, handle_event)

def handle_event(m):
    if m.text in eventPool:
        bot.send_message(m.chat.id, f"You chose {m.text}. Please wait a few seconds")
        global dota_event
        dota_event = parse.DotaEvent(parse.URL_OVERVIEW, [parse.URL_GROUPSTAGE_GAMES_1, parse.URL_GROUPSTAGE_GAMES_2], parse.URL_PLAYOFF)
        choosed[dota_event.get_event_name()] = list()
        handle_team(m, dota_event)
    else:
        bot.send_message(m.chat.id, "There is no such event")

def handle_team(m, event):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    team_list = [item for item in event.get_participants() if item not in choosed[dota_event.get_event_name()]]
    for i in range(len(team_list)):
        item = types.KeyboardButton(team_list[i])
        markup.add(item)
    message = bot.send_message(m.chat.id, f"Choose your favourite team now:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_team_choice, event)

def handle_team_choice(m, event):
    if m.text in event.get_participants():
        choosed[dota_event.get_event_name()].append(m.text)
        bot.send_message(m.chat.id, "Added!")
    else:
        bot.send_message(m.chat.id, "Error!")
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard = True)
    item_yes = types.KeyboardButton("Yes")
    item_no = types.KeyboardButton("No")
    markup.add(item_yes)
    markup.add(item_no)
    message = bot.send_message(m.chat.id, "Do you want to add another team?", reply_markup=markup)
    bot.register_next_step_handler(message, handle_choice_next, event)

def handle_choice_next(m, event):
    if m.text == "Yes":
        handle_team(m, event)
    else:
        bot.send_message(m.chat.id, "/showMatches")

    
if __name__ == '__main__':
    bot.infinity_polling()

# TODO admin account + method for adding an event
# TODO save knownusers?
# TODO database?
# TODO store chosen patterns?