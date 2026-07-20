import pandas as pd
import re
from datetime import datetime

from .scraping_common import fetch_soup, get_max_pages, scrape_paginated

# ここから物件1件分のHTMLから各項目を抜き出す関数

def extract_building_name(bukken):
    return bukken.find("h2",class_="property-detail-content__head-title").text

def extract_main_table(bukken):
    return [cell.get_text(strip=True) for cell in bukken.find("table",class_="property-detail-content_main").find_all("td")]

def extract_sub_table(bukken):
    return [cell.get_text(strip=True) for cell in bukken.find("table",class_="property-detail-content_sub").find_all("td")]

def extract_rooms_info(bukken):
    return bukken.find("table",class_="recommendTable").find_all("tr")[1:]

def extract_age(construction_date):
    built_year, built_month = map(int, construction_date[:-1].split("年"))
    return (datetime.now().year - built_year) + (datetime.now().month - built_month) / 12

def extract_price(price_text):
    return int(re.sub(r'[万円,]', '', price_text))

def extract_area(area_text):
    return float(re.sub(r'[m²,]', '', area_text))

def extract_eva(eva_text):
    eva_text = eva_text.strip()
    return int(re.sub(r'[万円割安,]', '', eva_text)) if eva_text not in ["相応","評価中"] else 0

def scrap_from_search(url):
    soup = fetch_soup(url)

    bukken_list=soup.find_all("li",class_="property-detail-list-item")
    bukken_results=[]

    for bukken in bukken_list:
        building_name=extract_building_name(bukken)
        address,_,construction_date,floor_max_min,num_rooms=extract_main_table(bukken)
        extract_sub_table(bukken)#現状未使用だが、テーブルが存在することの確認も兼ねている
        age=extract_age(construction_date)

        for room_info in extract_rooms_info(bukken):
            infos=[info.text for info in room_info.find_all("td")]

            if len(infos)!=9:
                continue

            _,_,price,unit_price,area,room_type,num_floor,dire,eva=infos

            price=extract_price(price)
            area=extract_area(area)

            bukken_results.append([
                building_name,
                price,
                address,
                age,
                area,
                price/area*3.306,
                room_type,
                num_floor,
                dire,
                extract_eva(eva),
                re.sub(r'\s+', '', floor_max_min),
                num_rooms,
            ])

    return bukken_results


def scrap_estate_data():
    WARD_NUM=23
    df_columns=["name","price","address","age","area","坪単価","部屋のタイプ","階数","向き","割安額","n階建て","戸数"]

    results_all=[]
    for n_ward in range(WARD_NUM):
        origin_url=f"https://www.mansion-review.jp/mansion/city/{659+n_ward}.html"
        soup = fetch_soup(origin_url)

        MAX_PAGES = get_max_pages(soup, "li.c-pagination-list__item")

        url="https://www.mansion-review.jp/mansion/city/{}_{}.html".format(659+n_ward,"{}")

        results_all.extend(scrape_paginated(url, MAX_PAGES, scrap_from_search, processes=8))

    return pd.DataFrame(results_all,columns=df_columns)

if __name__=="__main__":
    now = datetime.now()
    data=scrap_estate_data()

    lons,lats=get_lat_lon(data["住所"].values)
    data["lons"]=lons
    data["lats"]=lats

    data.to_csv(now.strftime("data/activelist/mansionreview_%Y%m%d.csv"))


