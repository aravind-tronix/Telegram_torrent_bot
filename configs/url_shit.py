import telegram


def my_bot():
    return telegram.Bot(token='your bot token')


def my_bot_token():
    return 'your bot token'


def scrap_master():
    return 'https://www.1377x.to/'


def movies_api():
    url = "https://api.themoviedb.org/3/movie/now_playing" #api reference https://www.themoviedb.org
    api_key = "api_key=your api key"
    language = "en-US"
    limit_page = "1"
    movies_api_url = f"{url}?{api_key}&language={language}&page={limit_page}"
    return movies_api_url
