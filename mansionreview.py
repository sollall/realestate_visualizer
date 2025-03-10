from bs4 import BeautifulSoup
from scrap import load_page
from multiprocessing import Pool
from tqdm import tqdm
import pandas as pd
import re
from datetime import datetime

from scrap import get_lat_lon

def scrap_from_search(url):
    
    html = load_page(url)
    soup = BeautifulSoup(html.content, 'html.parser')

    bukken_list=[bukken for bukken in soup.find_all("li",class_="property-detail-list-item")]
    bukken_results=[]

    for bukken in bukken_list:
        building_name=bukken.find("h2",class_="property-detail-content__head-title").text
        address,_,construction_date,floor_max_min,num_rooms=[cell.get_text(strip=True) for cell in bukken.find("table",class_="property-detail-content_main").find_all("td")]
        _,_,_,_,_,_=[cell.get_text(strip=True) for cell in bukken.find("table",class_="property-detail-content_sub").find_all("td")]

        rooms_info=[cell for cell in bukken.find("table",class_="recommendTable").find_all("tr")][1:]
    
        for room_info in rooms_info:
            infos=[info.text for info in room_info.find_all("td")]
            
            if len(infos)!=9:
                continue
            
            _,_,price,unit_price,area,room_type,num_floor,dire,eva=infos
        
            bukken_results.append([
                building_name,
                int(re.sub(r'[万円,]', '', price)),
                address,
                (lambda y, m: (datetime.now().year - y) + (datetime.now().month - m) / 12)(*map(int, construction_date[:-1].split("年"))),
                float(re.sub(r'[m²,]', '', area)),
                int(re.sub(r'[万円,]', '', price))/float(re.sub(r'[m²,]', '', area))*3.306,
                room_type,
                num_floor,
                dire,
                int(re.sub(r'[万円割安,]', '', eva.strip(),)) if eva.strip() not in ["相応","評価中"] else 0,
                re.sub(r'\s+', '', floor_max_min),
                num_rooms,
            ])
    
    return bukken_results


def get_estate_data_mansionreview():
    WARD_NUM=23

    results_all=[]
    for n_ward in range(WARD_NUM):
        origin_url=f"https://www.mansion-review.jp/mansion/city/{659+n_ward}.html"
        html = load_page(origin_url)
        soup = BeautifulSoup(html.content, 'html.parser')

        MAX_PAGES=int(soup.find_all("li",class_="c-pagination-list__item")[-1].text.strip())

        url="https://www.mansion-review.jp/mansion/city/{}_{}.html"
        
        with Pool(processes=8) as pool:
            with tqdm(total=MAX_PAGES-1) as pbar:
                for result in pool.imap(scrap_from_search, [url.format(659+n_ward,num) for num in range(1,MAX_PAGES)]):
                    results_all.extend(result)
                    pbar.update(1)        
        
        df_columns=["建物名","値段","住所","築年数","面積","坪単価","部屋のタイプ","階数","向き","割安額","n階建て","戸数"]

    return pd.DataFrame(results_all,columns=df_columns)

if __name__=="__main__":
    now = datetime.now()
    data=get_estate_data_mansionreview()

    lons,lats=get_lat_lon(data["住所"].values)
    data["lons"]=lons
    data["lats"]=lats

    data.to_csv(now.strftime("mansionreview/mansionreview_%Y%m%d.csv"))


