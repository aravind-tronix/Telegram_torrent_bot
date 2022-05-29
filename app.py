import telegram.bot
from telegram.ext import messagequeue as mq
import telegram
from telegram.ext import MessageHandler, Filters
from telegram.utils.request import Request
import os
from handlers.bot_handlers import *
from handlers.bot_messages import *
from configs.url_shit import my_bot_token


class MQBot(telegram.bot.Bot):
    '''A subclass of Bot which delegates send method handling to MQ'''

    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        '''Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments'''
        return super(MQBot, self).send_message(*args, **kwargs)


if __name__ == '__main__':
    token = my_bot_token()
    # limit global throughput to 3 messages per 3 seconds
    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    # set connection pool size for bot
    request = Request(con_pool_size=8)
    testbot = MQBot(token, request=request, mqueue=q)
    upd = telegram.ext.updater.Updater(bot=testbot, use_context=True)

    def reply(update, context):
        chatid = update["message"]["chat_id"]
        user_message = update["message"]["text"]
        if (user_message == "/start"):
            start(update, context, chatid)
        elif(user_message == "Top movies"):
            top_movies(chatid, context)
        elif(user_message == "Top apps"):
            popular_apps(chatid, context)
        elif(user_message == "now playing movies"):
            now_playing(chatid)
        elif(user_message == "/load_more"):
            load_more(chatid)
        elif(user_message == "Read me"):
            read_me(chatid)
        elif(user_message == "Privacy Policy"):
            privacy(chatid)
        elif(user_message == "Terms"):
            terms(chatid)

        else:
            search_engine(user_message,chatid, context)

    hdl = MessageHandler(Filters.text, reply)
    upd.dispatcher.add_handler(hdl)
    upd.start_polling()
