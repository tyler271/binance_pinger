from bs4 import BeautifulSoup
import copy
from datetime import datetime
import json
import requests
import time

class BinanceWebscraper:
    # Define class vars
    ts_format = "%Y-%m-%d %M:%S"
    announcement_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48"

    def get_latest_annoucement(self):
        url = BinanceWebscraper.announcement_url + "&pageNo=1&pageSize=1"
        r = requests.get(url)
        json_str = r.content.decode("utf-8")
        data = json.loads(json_str)
        article = data["data"]["articles"][0]
        return article["title"]

    def get_announcements_of_page(self, page_number=1):
        url = BinanceWebscraper.announcement_url + f"&pageNo={page_number}&pageSize=50"
        r = requests.get(url)
        json_str = r.content.decode("utf-8")
        data = json.loads(json_str)
        if data["data"]["total"] == 0:
            return None
        else:
            output_list = []
            article_list = data["data"]["articles"]
            for article in article_list:
                article_code = article["code"]
                title = article["title"]
                ts = get_article_timestamp(article_code)
                output_list.append({"article_code": article_code, "title": title, "ts": ts})
                time.sleep(0.5)
            return output_list

    def get_article_timestamp(self, article_code):
        url3 = f"https://www.binance.com/en/support/announcement/{article_code}"
        page = requests.get(url3)
        soup = BeautifulSoup(page.content, "html.parser")
        ts_str = soup.select(".css-17s7mnd")[0].text
        ts = datetime.strptime(ts_str, TS_FORMAT)
        return ts
