from bs4 import BeautifulSoup
from multiprocessing import Pool
from tqdm import tqdm
import pandas as pd
import re
from datetime import datetime

from .utils import load_page


class MansionReviewScrapeError(Exception):
    """mansion-review.jpのHTML構造が想定と異なり、スクレイピングを継続できない場合に送出する"""


def _find_required(parent, name, url, **kwargs):
    """要素が見つからない場合、どのタグ・クラスがどのURLで見つからなかったかを明示して例外を送出する"""
    element = parent.find(name, **kwargs)
    if element is None:
        attrs = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        raise MansionReviewScrapeError(
            f"要素が見つかりません(tag={name}, {attrs}) url={url}\n"
            "mansion-review.jpのHTML構造が変更された可能性があります。"
        )
    return element


def scrap_from_search(url):

    html = load_page(url)
    soup = BeautifulSoup(html.content, 'html.parser')

    bukken_list=[bukken for bukken in soup.find_all("li",class_="property-detail-list-item")]
    if not bukken_list:
        raise MansionReviewScrapeError(
            f"物件一覧(property-detail-list-item)が0件でした url={url}\n"
            "mansion-review.jpのHTML構造が変更された可能性があります。"
        )
    bukken_results=[]

    for bukken in bukken_list:
        building_name=_find_required(bukken,"h2",url,class_="property-detail-content__head-title").text
        address,_,construction_date,floor_max_min,num_rooms=[cell.get_text(strip=True) for cell in _find_required(bukken,"table",url,class_="property-detail-content_main").find_all("td")]
        _,_,_,_,_,_=[cell.get_text(strip=True) for cell in _find_required(bukken,"table",url,class_="property-detail-content_sub").find_all("td")]

        rooms_info=[cell for cell in _find_required(bukken,"table",url,class_="recommendTable").find_all("tr")][1:]

        for room_info in rooms_info:
            infos=[info.text for info in room_info.find_all("td")]

            # 「全件を表示する」ボタン行(1列)や未登録会員向けモザイク行(6列)など、
            # 価格〜価格評価の9列が揃っていない行はデータを持たないのでスキップする。
            # 末尾に「情報取得日」等の列が追加されていても、先頭9列は変わらず使える。
            if len(infos)<9:
                continue

            _,_,price,unit_price,area,room_type,num_floor,dire,eva=infos[:9]
        
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


def scrap_estate_data():
    WARD_NUM=23

    results_all=[]
    for n_ward in range(WARD_NUM):
        origin_url=f"https://www.mansion-review.jp/mansion/city/{659+n_ward}.html"
        html = load_page(origin_url)
        soup = BeautifulSoup(html.content, 'html.parser')

        pagination_items=soup.find_all("li",class_="c-pagination-list__item")
        if not pagination_items:
            raise MansionReviewScrapeError(
                f"ページネーション要素(c-pagination-list__item)が見つかりません url={origin_url}\n"
                "mansion-review.jpのHTML構造が変更された可能性があります。"
            )
        MAX_PAGES=int(pagination_items[-1].text.strip())

        url="https://www.mansion-review.jp/mansion/city/{}_{}.html"
        
        with Pool(processes=8) as pool:
            with tqdm(total=MAX_PAGES-1) as pbar:
                for result in pool.imap(scrap_from_search, [url.format(659+n_ward,num) for num in range(1,MAX_PAGES)]):
                    results_all.extend(result)
                    pbar.update(1)        
        
        #["name","price","address","area","age"]が必須?
        df_columns=["name","price","address","age","area","坪単価","部屋のタイプ","階数","向き","割安額","n階建て","戸数"]
        

    return pd.DataFrame(results_all,columns=df_columns)

if __name__=="__main__":
    now = datetime.now()
    data=scrap_estate_data()

    lons,lats=get_lat_lon(data["住所"].values)
    data["lons"]=lons
    data["lats"]=lats

    data.to_csv(now.strftime("data/activelist/mansionreview_%Y%m%d.csv"))


