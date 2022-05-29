from configs.url_shit import my_bot
import telegram
from telegram import ReplyKeyboardMarkup

telegram_username = "Contact admin @your_telegram_user_name" #replace with your username


def welcome(chatid):
    welcome = "Hi! What data do you want? type in for a search or choose from the below keyboard buttons."
    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[['Read me'], [
                                 'now playing movies'], ['Top movies', "Top apps"], ["Privacy Policy", "Terms"]])
    my_bot().send_message(chatid, welcome,
                        reply_markup=markup)


def read_me(chatid):
    readme = f'''Welcome to Torrent Bot. Here are some clarifications\n\n
            <b>Do i need a vpn to use this bot?</b>\n
            No. You do not require a vpn to use this bot\n\n
            <b>Why some of the toorent files are showing
            page not found?</b>\n
            Some of the ISP might block the links. 
            If you cant download the .torrent file please
            use a vpn.
            {telegram_username}
            '''
    my_bot().send_message(chatid, readme,
                        parse_mode=telegram.ParseMode.HTML)


def privacy(chatid):
    privacy = f'''Welcome to Torrent Bot. Our privacy policy\n\n
            We dont care what you search using
            our bot. We don't store your data and 
            Queries.
            {telegram_username}
            '''
    my_bot().send_message(chatid, privacy,
                        parse_mode=telegram.ParseMode.HTML)


def terms(chatid):
    terms = f'''Welcome to Torrent Bot. Terms of use\n\n
            We are not responsible for the contents
            you see/download using our bot.
            {telegram_username}
            '''
    my_bot().send_message(chatid, terms,
                        parse_mode=telegram.ParseMode.HTML)
