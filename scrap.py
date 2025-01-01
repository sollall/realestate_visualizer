import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from retry import retry
from tqdm import tqdm
import urllib


# 面積を抽出する関数
def extract_area(text):
    match = re.search(r'(\d+(\.\d+)?)m2', text)
    if match:
        return float(match.group(1))
    return None

extract_area("50.00m2　（15.13m2）")

def extract_name(text):
    return text.split()[0]

extract_name("給田西住宅\u3000１号棟")

def extract_price(text):
    text = text.strip()
    match = re.search(r'((\d+)億)?\s*((\d+)万)?', text)
    if match:
        oku = int(match.group(2)) * 100000000 if match.group(2) else 0
        man = int(match.group(4)) * 10000 if match.group(4) else 0
        return oku + man
    return None

def calculate_age(built_date):
    # 現在の年と月を取得
    current_date = datetime.now()
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

    return age_years,age_months

# リクエストがうまく行かないパターンを回避するためのやり直し
@retry(tries=3, delay=10, backoff=2)
def load_page(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    return soup

def get_estate_data_suumo(pages):
    # SUUMOを東京都23区のみ指定して検索して出力した画面のurl(ページ数フォーマットが必要)
    url = "https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/?ar=030&bs=011&ta=13&jspIdFlg=patternShikugun&sc=13101&sc=13102&sc=13103&sc=13104&sc=13105&sc=13113&sc=13106&sc=13107&sc=13108&sc=13118&sc=13121&sc=13122&sc=13123&sc=13109&sc=13110&sc=13111&sc=13112&sc=13114&sc=13115&sc=13120&sc=13116&sc=13117&sc=13119&kb=1&kt=9999999&mb=0&mt=9999999&ekTjCd=&ekTjNm=&tj=0&cnb=0&cn=9999999&srch_navi={{2}}&page={}"
    ESTATES_MAX=30
    info={"name":[],
          "price":[],
          "address":[],
          "area":[],
          "age_years":[],
          "age_months":[],
          "price per unit area":[]
          }

    for page in tqdm(range(1,pages+1)):
        soup = load_page(url.format(page))
        estates_groups = soup.find("div",class_='property_unit_group')
        estates = estates_groups.find_all('div', class_='property_unit')

        for i in range(ESTATES_MAX):
            estate=estates[i].find_all('div', class_='dottable-line')

            
            name_text=estate[0].find_all("dd")[0].text
            info["name"].append(extract_name(name_text))
            price_text=estate[1].find_all("dd")[0].text

            info["price"].append(extract_price(price_text))
            info["address"].append(estate[2].find_all("dd")[0].text)
            area_text=estate[3].find_all("dd")[0].text
            info["area"].append(extract_area(area_text))
            built_date=estate[4].find_all("dd")[1].text
            age_years,age_months=calculate_age(built_date)
            info["age_years"].append(age_years)
            info["age_months"].append(age_months)
            info["price per unit area"].append(float(info["price"][-1])/float(info["area"][-1])*3.30578)

    return pd.DataFrame(info)

def get_lat_lon(addresses):

    @retry(tries=3, delay=10, backoff=2)
    def _load_page(url):
        response = requests.get(url)
        return response

    lons=[]
    lats=[]
    
    for address in tqdm(addresses):
        makeUrl = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
        s_quote = urllib.parse.quote(address)
        response=_load_page(makeUrl + s_quote)
        lon,lat=response.json()[0]["geometry"]["coordinates"]

        lons.append(lon)
        lats.append(lat)
    
    return lons,lats