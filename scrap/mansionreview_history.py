from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from utils import load_page
import multiprocessing
from multiprocessing import Pool
from queue import Queue
from tqdm import tqdm
import pandas as pd
import re
from datetime import datetime
import time
import threading
import argparse

import password


def signin_browser():
    #googlechromeを起動
    browser = webdriver.Chrome()
    #timeoutを設定
    browser.command_executor.set_timeout(1000)
    #chromeドライバーが見つかるまでの待ち時間を設定
    browser.implicitly_wait(3)

    #一旦サインイン
    login_url="https://www.mansion-review.jp/login/"

    browser.get(login_url)
    time.sleep(3)

    input_email = browser.find_element(By.XPATH,'//*[@id="mainEntryBlock"]/div/form/div[1]/div[2]/input')
    input_email.send_keys(password.MAILADDRESS)

    input_password = browser.find_element(By.XPATH,'//*[@id="mainEntryBlock"]/div/form/div[2]/div[2]/input')
    input_password.send_keys(password.PASSWORD)

    signin_btn = browser.find_element(By.XPATH,'//*[@id="mainEntryBlock"]/div/form/div[3]/div/div/input')
    signin_btn.click()

    return browser

def get_bukken_history(browser,url):
    browser.get(url)
    time.sleep(3)

    try:
        contract_history=browser.find_element(By.CLASS_NAME,'more_button cta_button_a')
        browser.execute_script("arguments[0].click();", contract_history)
    except NoSuchElementException:
        pass

    html = browser.page_source
    soup = BeautifulSoup(html, 'html.parser')

    bukken_name=soup.find("span",class_="title_span").text
    bukken_infos=[]

    try:
        bukken_html_list=soup.find("table",class_="tekisei_kakaku_sindan_list_area table_heading_fixed js_table_heading_fixed js_sticky_detection").find_all("tr")[1:-2]
        for bukken_html in bukken_html_list:
            bukken_td=bukken_html.find_all("td")
            bukken_info=[bukken_name]+[item.text for item in bukken_td]
            bukken_infos.append(bukken_info)
    except AttributeError:
        pass

    return bukken_infos

# 初期化: マネージャーQueueでブラウザを共有
def init_browser_queue(num_browsers):
    browser_queue = Queue()

    # 事前に複数のブラウザを作成してキューに入れる
    for _ in range(num_browsers):
        browser = signin_browser()
        browser_queue.put(browser)

    return browser_queue

# ワーカー関数: キューからブラウザを取得して処理
def wrap(url):
    global browser_queue
    browser = browser_queue.get()  # 空いているブラウザを取得
    try:
        result_queue.put(get_bukken_history(browser,url))
    finally:
        browser_queue.put(browser)  # 使い終わったらキューに戻す

def scrap_from_search(search_url):

    results_all=[]
    threads = []

    html = load_page(search_url)
    soup = BeautifulSoup(html.content, 'html.parser')

    bukken_list=soup.find_all("h2",class_="property-detail-content__head-title")
    urls=[bukken.find("a")["href"] for bukken in bukken_list]

    for i, url in enumerate(urls):
        thread = threading.Thread(target=wrap, args=(url,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

    return results_all

def clean_text(text):
    # タブや改行をスペースに置き換え、不要なスペースを削除
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned

def to_format_url(original_url: str) -> str:
    if not original_url.endswith(".html"):
        raise ValueError("URLが .html で終わっていません")

    base = original_url[:-5]  # ".html" を取り除く
    return f"{base}_{{}}.html"



if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("search_url", help="検索用のURLを指定してください")
    args = parser.parse_args()

    search_url = args.search_url

    html = load_page(search_url)
    soup = BeautifulSoup(html.content, 'html.parser')
    file_name=re.sub(r'の中古マンションランキング.*', '', soup.find("title").text.strip())
    print(f"ファイル名: {file_name}")
    MAX_PAGES=int(soup.find_all("li",class_="c-pagination-list__item")[-1].text.strip())

    search_url_format=to_format_url(search_url)
    search_urls=[search_url_format.format(num) for num in range(1,MAX_PAGES+1)]

    MAX_PARA=8#multiprocessing.cpu_count()
    browser_queue=init_browser_queue(MAX_PARA)
    result_queue = Queue()

    # tqdmの進捗バー
    progress_bar = tqdm(total=len(search_urls))
    

    for url in search_urls:
        scrap_from_search(url)
        progress_bar.update(1)

    # 結果を取得
    pre_dataframe=[]
    while not result_queue.empty():
        result = result_queue.get()
        pre_dataframe.extend(result)

    df=pd.DataFrame(pre_dataframe,columns=[  "建物名",
                                             "id",
                                             "販売年月",
                                             "販売終了年月",
                                             "所在階",
                                             "間取り",
                                             "向き",
                                             "特徴",
                                             "専有面積",
                                             "バルコニー面積",
                                             "販売価格",
                                             "価格変更履歴",
                                             "坪単価",
                                             "㎡単価",
                                             "管理費(㎡管理費)",
                                             "修繕積立金(㎡修繕積立金)"
                                            ])
    
    df["販売終了年月"]=df["販売終了年月"].apply(clean_text)
    df.to_csv(f"data/transactionhistory/{file_name}.csv")