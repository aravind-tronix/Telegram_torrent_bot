import json
import asyncio
import httpx
import os
import requests

TOKEN = os.environ.get('tg_bot_token')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
MOVIES = 'https://www.1377x.to/popular-movies'


async def send_telegram_message(chat_id, text, keyboard=None):
    """ Sends a message to a Telegram chat with an optional keyboard and delay to respect rate limits """
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard if keyboard else None
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f'{TELEGRAM_API_URL}/sendMessage', json=payload)

        data = response.json()

        if response.status_code != 200 or not data.get("ok"):
            print(f"Error sending message: {data}")
            return None

        return data["result"]["message_id"]

    # Delay to respect Telegram rate limits (e.g., 1 message per second)
    await asyncio.sleep(1)


async def edit_telegram_message(chat_id, message_id, new_text):
    """ Edits an existing message """
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{TELEGRAM_API_URL}editMessageText", json=payload)

        if response.status_code != 200:
            print(f"Error editing message: {response.json()}")


def lambda_handler(event, context):
    """ AWS Lambda entry point """
    print("Received event:", json.dumps(event))

    # Extract Telegram update
    # body = json.loads(event)
    chat_id = event.get("message", {}).get("chat", {}).get("id")
    user_message = event.get("message", {}).get("text", "")

    if not chat_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid request, chat_id not found"})}

    # Process user input
    if (user_message == "/start"):
        # result = start(chat_id)
        # print(type(result))
        reply_text = "Hello! Choose an option:"
        keyboard = {
            "keyboard": [['Read me'], [
                'now playing movies'], ['Top movies', "Top apps"], ["Privacy Policy", "Terms"]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }

        # Send message with optional keyboard
        asyncio.run(send_telegram_message(chat_id, reply_text, keyboard))
    elif (user_message == "Top movies"):
        top, toplink, name, fname, size = [], [], [], [], []
        page = requests.get(MOVIES)
        soup = BeautifulSoup(page.content, 'html.parser')
        # asyncio.run(send_telegram_message(chat_id,message))
        message_id = asyncio.run(send_telegram_message(
            chat_id, "Please wait..Fetching data"))
        # update1 = bot1.send_message(chatid, "Please wait..Fetching data")
        for div in soup.find_all("div", {"class": "table-list-wrap"}):
            for div1 in div.find_all("a", {"class": None}):
                if div1.has_attr('href'):
                    top.append(div1["href"])
        subs = "torrent"
        res = [i for i in top if subs in i]

        for query in res:
            URL1 = "https://www.1377x.to/"+query
            page = requests.get(URL1)
            soup = BeautifulSoup(page.content, 'html.parser')
            for div in soup.find_all("div", {"class": "l30719a994ed675b3e5543484a83d6141b0edb709 clearfix"}):
                for div1 in div.find_all("a", {"onclick": "javascript: void(0);"}):
                    if div1.has_attr('href'):
                        toplink.append(div1["href"])
            for div in soup.find("strong", text="Total size").next_sibling:
                a = str(div)
                size.append(a)
        subs = "magnet"
        res1 = [i for i in toplink if subs in i]
        # await edit_telegram_message(chat_id, message_id, "hello")
        asyncio.run(edit_telegram_message(chat_id, message_id, "message"))
        # bot1.edit_message_text(
        #     chat_id=chatid, message_id=update1["message_id"], text="queueing data")

        page = requests.get(MOVIES)
        soup = BeautifulSoup(page.content, 'html.parser')
        for div in soup.find_all("div", {"class": "table-list-wrap"}):
            for div1 in div.find_all("a", {"class": None}):
                if div1.has_attr('href'):
                    name.append(div1.text)
        res2 = [i for i in range(len(name)) if i % 2 == 0]
        asyncio.run(edit_telegram_message(chat_id, message_id, "running"))
        for odd in res2:
            fname.append(name[odd])

        for (fname, res1, size) in zip(fname, res1, size):
            asyncio.run(send_telegram_message(chat_id, message_id, fname))

        #     context.bot.send_message(chat_id=chatid, text="Title:"+"<u>"+fname+"</u>"+"\n\n" +
        #                                 "<b>LINK:</b>"+"\n\n"+"<code>"+res1+"</code>"+"\n\n"+"size:"+size, parse_mode=telegram.ParseMode.HTML)
        # context.bot.send_message(chat_id=chatid, text="Feedbacks are welcomed. Contact Admin\n @aravind_at_telegram",
        #                             parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)
    elif (user_message == "Top apps"):
        popular_apps(chat_id, context)
    elif (user_message == "now playing movies"):
        now_playing(chat_id)
    elif (user_message == "/load_more"):
        load_more(chat_id)
    elif (user_message == "Read me"):
        read_me(chat_id)
    elif (user_message == "Privacy Policy"):
        privacy(chat_id)
    elif (user_message == "Terms"):
        terms(chat_id)

    else:
        search_engine(user_message, chatid, context)

    # Send message asynchronously
    asyncio.run(send_telegram_message(chat_id, reply_text))

    return {"statusCode": 200, "body": json.dumps({"message": "Processed successfully"})}
