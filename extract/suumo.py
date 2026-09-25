import pandas as pd
import re
from datetime import datetime
from bs4 import BeautifulSoup
from multiprocessing import Pool
from tqdm import tqdm

from .utils import load_page

# 面積を抽出する関数
def extract_area(text):
    match = re.search(r'(\d+(\.\d+)?)m2', text)
    if match:
        return float(match.group(1))
    return None

def extract_name(text):
    return text

def extract_price(text):
    """「1億2000万円」→120000000のように価格テキストを円に変換する

    「価格未定」など数字を含まないものはNoneを返す。
    「5000万円～6000万円」のような価格帯は先頭(下限)の値を採用する。
    """
    text = text.strip().replace(",", "")
    match = re.search(r'(\d+)億\s*(?:(\d+)万)?|(\d+)万', text)
    if not match:
        return None
    if match.group(1):
        oku = int(match.group(1)) * 100000000
        man = int(match.group(2)) * 10000 if match.group(2) else 0
        return oku + man
    return int(match.group(3)) * 10000

def calculate_age(built_date, current_date=None):
    # 現在の年と月を取得
    current_date = current_date or datetime.now()
    current_year = current_date.year
    current_month = current_date.month

    # built_dateを年と月に分割
    match = re.search(r'(\d+)年(\d+)月', built_date)
    if match:
        built_year = int(match.group(1))
        built_month = int(match.group(2))
    else:
        return None,None
    
    # 築年数を計算
    age_years = current_year - built_year
    age_months = current_month - built_month

    # 月の差がマイナスの場合、年から1を引き、月に12を足す
    if age_months < 0:
        age_years -= 1
        age_months += 12

    # 「2027年3月予定」のような未完成の新築は築年数が負になるため扱わない
    if age_years < 0:
        return None,None

    return age_years,age_months

def read_page(page_url):
    #ここで並列化したい

    html = load_page(page_url)
    soup = BeautifulSoup(html.content, 'html.parser')
    estates_groups = soup.find("div",class_='property_unit_group')
    estates = estates_groups.find_all('div', class_='property_unit')

    results=[]
    
    for estate in estates:
        estate_info=estate.find_all('div', class_='dottable-line')

        name_text=estate_info[0].find_all("dd")[0].text
        name=extract_name(name_text)
        
        price_text=estate_info[1].find_all("dd")[0].text
        price=extract_price(price_text)

        adress=estate_info[2].find_all("dd")[0].text

        area_text=estate_info[3].find_all("dd")[0].text
        area=extract_area(area_text)
        
        built_date=estate_info[4].find_all("dd")[1].text
        age_years,age_months=calculate_age(built_date)

        results.append([
            name,
            price,
            adress,
            area,
            age_years,
            age_months,
        ])

    return results

def get_estate_data():
    # SUUMOを東京都23区のみ指定して検索して出力した画面のurl(ページ数フォーマットが必要)
    url = "https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/?ar=030&bs=011&ta=13&jspIdFlg=patternShikugun&sc=13101&sc=13102&sc=13103&sc=13104&sc=13105&sc=13113&sc=13106&sc=13107&sc=13108&sc=13118&sc=13121&sc=13122&sc=13123&sc=13109&sc=13110&sc=13111&sc=13112&sc=13114&sc=13115&sc=13120&sc=13116&sc=13117&sc=13119&kb=1&kt=9999999&mb=0&mt=9999999&ekTjCd=&ekTjNm=&tj=0&cnb=0&cn=9999999&srch_navi={{2}}&page={}"
    html = load_page(url.format(1))#1ページ目を取得してページ数を取得
    soup = BeautifulSoup(html.content, 'html.parser')
    MAX_PAGES=int(soup.find("ol",class_="pagination-parts").find_all("li")[-1].text)

    with Pool(processes=3) as pool:
        results_all=[]
        with tqdm(total=MAX_PAGES) as pbar:
            for result in pool.imap(read_page, [url.format(num) for num in range(1,MAX_PAGES)]):
                results_all.extend(result)
                pbar.update(1)

    data = pd.DataFrame(results_all,columns=["name","price","address","area","age","age_months"])
    return drop_unparsable(data)

def drop_unparsable(data):
    """価格未定・未完成の新築など、数値に変換できなかった物件を除く

    全件がパース失敗した場合は空になり、validate_rawでHTML構造の変化として検知される。
    """
    parsed = data.dropna(subset=["price", "area", "age"])
    dropped = len(data) - len(parsed)
    if dropped:
        print(f"価格・面積・築年を読み取れなかった{dropped}件を除外しました")
    return parsed.reset_index(drop=True)

if __name__=="__main__":
    now = datetime.now()
    data=get_estate_data()

    data["price per unit area"]=data["price"]/data["area"]*3.30578
    lons,lats=get_lat_lon(data["address"].values)
    data["lons"]=lons
    data["lats"]=lats

    data.to_csv(now.strftime("data/activelist/suumo_%Y%m%d.csv"))

    

