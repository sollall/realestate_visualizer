from bs4 import BeautifulSoup
from scrap import load_page
from multiprocessing import Pool
from tqdm import tqdm
import pandas as pd
from datetime import datetime

#検索画面のスクレイピングと個別物件のスクレイピングを行う必要がある
def scrap_from_search(url):
    
    # 検索画面のスクレイピング
    html = load_page(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    
    bukken_list=[[bukken.find("div",class_="building_name").text,bukken.find("div",class_="building_spec").find("table").find_all("tr")[0].address.text,bukken.find("a")["href"]] 
                 for bukken in soup.find_all("section",class_="building_detail_for_search_list")]

    room_infos=[]
    for name,address,page_id in bukken_list:
        bukken_url=f"https://mansion-market.com{page_id}"

        bukken_html = load_page(bukken_url)
        bukken_soup = BeautifulSoup(bukken_html.content, 'html.parser')

        if bukken_soup.find("section",class_="detail_trade_price"):
            room_list=bukken_soup.find("section",class_="detail_trade_price").find("table").find_all("tr")[1:]
            for room in room_list:
                room_info=[item.text for item in room.find_all("td")]

                room_infos.append([name,address]+room_info)

    return room_infos

def get_estate_data_mansionmarket(url):
    html = load_page(url)
    soup = BeautifulSoup(html.content, 'html.parser')

    MAX_PAGES=int(soup.find("li",class_="page last").text)

    url_format=url+"/page/{}"
    
    results_all=[]
    with Pool(processes=8) as pool:
        with tqdm(total=MAX_PAGES-1) as pbar:
            for result in pool.imap(scrap_from_search, [url_format.format(num) for num in range(1,MAX_PAGES)]):
                results_all.extend(result)
                pbar.update(1)   
    
    df_columns=["建物名","住所","約定日","価格","階数","間取り","面積","単価","方角","リノベ"]

    return pd.DataFrame(results_all,columns=df_columns)

if __name__=="__main__":
    url="https://mansion-market.com/mansions/areas/tokyo/taito"
    now = datetime.now()
    data=get_estate_data_mansionmarket(url)

    data.to_csv(now.strftime("temmp_%Y%m%d.csv"))

