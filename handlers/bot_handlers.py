from configs.url_shit import my_bot, scrap_master, movies_api
from configs.blah_blah import welcome
from handlers.letme_handle import listToString
from bs4 import BeautifulSoup
import requests
import telegram
import telegram.bot
import json
import random


def start(chatid):
    
    welcome(chatid)


def top_movies(chatid, context):
    results, result_links, name, fname, size = [], [], [], [], []
    page = requests.get(f"{scrap_master()}popular-movies")
    soup = BeautifulSoup(page.content, 'html.parser')
    update1 = my_bot().send_message(chatid, "Please wait..Fetching data")
    for div in soup.find_all("div", {"class": "table-list-wrap"}):
        for div1 in div.find_all("a", {"class": None}):
            if div1.has_attr('href'):
                results.append(div1["href"])
    subs = "torrent"
    res = [i for i in results if subs in i]

    for query in res:
        URL1 = f"{scrap_master()}{query}"
        page = requests.get(URL1)
        soup = BeautifulSoup(page.content, 'html.parser')
        for div in soup.find_all("div", {"class": "l30719a994ed675b3e5543484a83d6141b0edb709 clearfix"}):
            for div1 in div.find_all("a", {"onclick": "javascript: void(0);"}):
                if div1.has_attr('href'):
                    result_links.append(div1["href"])
        for div in soup.find("strong", text="Total size").next_sibling:
            convert = str(div)
            size.append(convert)
    subs = "magnet"
    res1 = [i for i in result_links if subs in i]
    my_bot().edit_message_text(
        chat_id=chatid, message_id=update1["message_id"], text="queueing data")

    page = requests.get(f"{scrap_master()}popular-movies")
    soup = BeautifulSoup(page.content, 'html.parser')
    for div in soup.find_all("div", {"class": "table-list-wrap"}):
        for div1 in div.find_all("a", {"class": None}):
            if div1.has_attr('href'):
                name.append(div1.text)
    res2 = [i for i in range(len(name)) if i % 2 == 0]
    my_bot().edit_message_text(
        chat_id=chatid, message_id=update1["message_id"], text="pushing data......")
    for odd in res2:
        fname.append(name[odd])
    for (fname, res1, size) in zip(fname, res1, size):
        context.bot.send_message(chat_id=chatid, text="Title:"+"<u>"+fname+"</u>"+"\n\n" +
                                 "<b>LINK:</b>"+"\n\n"+"<code>"+res1+"</code>"+"\n\n"+"size:"+size, parse_mode=telegram.ParseMode.HTML)
    context.bot.send_message(chat_id=chatid, text="Feedbacks are welcomed. Contact Admin\n @aravind_at_telegram",
                             parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)


def popular_apps(chatid, context):
    results, result_links, name, fname, size = [], [], [], [], []
    URL = f"{scrap_master()}popular-apps"
    update1 = my_bot().send_message(chatid, "Please wait..Fetching data")
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    for div in soup.find_all("div", {"class": "table-list-wrap"}):
        for div1 in div.find_all("a", {"class": None}):
            if div1.has_attr('href'):
                results.append(div1["href"])
    subs = "torrent"
    res = [i for i in results if subs in i]
    my_bot().edit_message_text(
        chat_id=chatid, message_id=update1["message_id"], text="queueing data")

    for query in res:
        URL1 = f"{scrap_master()}{query}"
        page = requests.get(URL1)
        soup = BeautifulSoup(page.content, 'html.parser')
        for div in soup.find_all("div", {"class": "l30719a994ed675b3e5543484a83d6141b0edb709 clearfix"}):
            for div1 in div.find_all("a", {"onclick": "javascript: void(0);"}):
                if div1.has_attr('href'):
                    result_links.append(div1["href"])
        for div in soup.find("strong", text="Total size").next_sibling:
            convert = str(div)
            size.append(convert)
    subs = "magnet"
    res1 = [i for i in result_links if subs in i]
    my_bot().edit_message_text(
        chat_id=chatid, message_id=update1["message_id"], text="pushing data......")

    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    for div in soup.find_all("div", {"class": "table-list-wrap"}):
        for div1 in div.find_all("a", {"class": None}):
            if div1.has_attr('href'):
                name.append(div1.text)
    res2 = [i for i in range(len(name)) if i % 2 == 0]
    for odd in res2:
        fname.append(name[odd])

    for (fname, res1, size) in zip(fname, res1, size):
        context.bot.send_message(chat_id=chatid, text="Title:"+"<u>"+fname+"</u>"+"\n\n" +
                                 "<b>LINK:</b>"+"\n\n"+"<code>"+res1+"</code>"+"\n"+"size:"+size, parse_mode=telegram.ParseMode.HTML)
    context.bot.send_message(chat_id=chatid, text="Feedbacks are welcomed. Contact Admin\n @aravind_at_telegram",
                             parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)


def now_playing(chatid):
    movies_all = {}
    final_data = []
    url = movies_api()
    response1 = requests.request("GET", url)
    data1 = json.loads(response1.text)
    movies = data1["results"]
    for movie in movies:
        movies_under = movie["title"].replace(" ", "_")
        movies_all["title"] = "/"+movies_under
        movies_all["release_date"] = movie["release_date"]
        send_data = json.dumps(movies_all).strip(
            '{}').replace(',', '\n').replace('"', '')
        final_data.append(send_data+"\n\n")
    final_str = listToString(final_data)
    my_bot().send_message(chatid, text="Click a movie name to copy. Paste and get torrent links." +
                        "\n\n"+final_str, parse_mode=telegram.ParseMode.HTML)
    my_bot().send_message(chatid, 'show more movies?\n\n'+"/load_more")


def load_more(chatid):
    movies_all = {}
    final_data = []
    check = movies_api()
    response1 = requests.request("GET", check)
    data1 = json.loads(response1.text)
    page = data1["total_pages"]
    search = random.randint(0, page)
    url = "https://api.themoviedb.org/3/movie/now_playing?api_key=cc348043650d1146104248ee9c810fa6&language=en-US&page=" + \
        str(search)
    response1 = requests.request("GET", url)
    data1 = json.loads(response1.text)
    movies = data1["results"]
    for movie in movies:
        movies_under = movie["title"].replace(" ", "_")
        movies_all["title"] = "/"+movies_under
        movies_all["release_date"] = movie["release_date"]
        send_data = json.dumps(movies_all).strip(
            '{}').replace(',', '\n').replace('"', '')
        final_data.append(send_data+"\n\n")
    final_str = listToString(final_data)
    my_bot().send_message(chatid, text="Click a movie name to get torrent links." +
                        "\n\n"+final_str, parse_mode=telegram.ParseMode.HTML)
    my_bot().send_message(chatid, 'show more movies?\n\n'+"/load_more")


def search_engine(user_message,chatid, context):
    user_message = user_message.replace("_", " ").replace("/", "")
    URL = f'{scrap_master()}/search/'+user_message+'/1/'
    results, result_links, name, fname, seeders, size = [], [], [], [], [], []
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    update1 = my_bot().send_message(chatid, "Please wait..Fetching data")

    for div in soup.find_all("div", {"class": "table-list-wrap"}):
        for div1 in div.find_all("a", {"class": None}):
            if div1.has_attr('href'):
                results.append(div1["href"])
    subs = "torrent"
    res = [i for i in results if subs in i]

    for query in res:
        URL1 = "https://www.1377x.to/"+query
        page = requests.get(URL1)
        soup = BeautifulSoup(page.content, 'html.parser')
        for div in soup.find_all("div", {"class": "l30719a994ed675b3e5543484a83d6141b0edb709 clearfix"}):
            for div1 in div.find_all("a", {"onclick": "javascript: void(0);"}):
                if div1.has_attr('href'):
                    result_links.append(div1["href"])
            for div in soup.find_all("span", {"class": "seeds"}):
                convert = str(div)
                convert = (convert[20:])
                seed = convert[:-7]
                seeders.append(seed)
            for div in soup.find("strong", text="Total size").next_sibling:
                convert = str(div)
                size.append(convert)
    my_bot().edit_message_text(
        chat_id=chatid, message_id=update1["message_id"], text="pushing data......")

    subs = "magnet"
    res1 = [i for i in result_links if subs in i]

    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    for div in soup.find_all("div", {"class": "table-list-wrap"}):
        for div1 in div.find_all("a", {"class": None}):
            if div1.has_attr('href'):
                name.append(div1.text)
    res2 = [i for i in range(len(name)) if i % 2 == 0]
    for odd in res2:
        fname.append(name[odd])

    if(len(seeders) != 0):
        for (fname, res1, seeders, size) in zip(fname, res1, seeders, size):
            context.bot.send_message(chat_id=chatid, text="title:"+"<b>"+fname+"</b>"+"\n"+"seeders:"+"<b>" +
                                     seeders+"</b>"+"\n"+"links:"+"<code>"+res1+"</code>"+"\n"+"\n"+"size:"+size, parse_mode=telegram.ParseMode.HTML)
        context.bot.send_message(chat_id=chatid, text="Feedbacks are welcomed. Contact Admin\n @aravind_at_telegram",
                                 parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=True)
    else:
        context.bot.send_message(
            chat_id=chatid, text="Oops!!. no data found ☹️. Please check the spelling")
