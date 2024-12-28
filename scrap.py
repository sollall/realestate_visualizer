import requests
from bs4 import BeautifulSoup
from retry import retry
import urllib
import time
import logging

import numpy as np

# 複数ページの情報をまとめて取得
data_samples = []

# スクレイピングするページ数
max_page = 2000
# SUUMOを東京都23区のみ指定して検索して出力した画面のurl(ページ数フォーマットが必要)
url = "https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/?ar=030&bs=011&ta=13&jspIdFlg=patternShikugun&sc=13101&sc=13102&sc=13103&sc=13104&sc=13105&sc=13113&sc=13106&sc=13107&sc=13108&sc=13118&sc=13121&sc=13122&sc=13123&sc=13109&sc=13110&sc=13111&sc=13112&sc=13114&sc=13115&sc=13120&sc=13116&sc=13117&sc=13119&kb=1&kt=9999999&mb=0&mt=9999999&ekTjCd=&ekTjNm=&tj=0&cnb=0&cn=9999999&srch_navi={{2}}&page={}"


# リクエストがうまく行かないパターンを回避するためのやり直し
@retry(tries=3, delay=10, backoff=2)
def load_page(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    return soup

# 処理時間を測りたい
start = time.time()
times = []

# ページごとの処理
#for page in range(1,max_page+1):
for page in range(1,3):
    before = time.time()
    # ページ情報
    soup = load_page(url.format(page))
    # 物件情報リストを指定
    div_estates = soup.find("div",class_='ui-media')
    estates=div_estates.find_all("div",class_='property')
    print(estates)
    # 物件ごとの処理
    for estate in estates:

        # 建物情報
        data_home = {}
        # カテゴリ
        data_home["cat"]=estate.find(class_='ui-pct ui-pct--util1').text
        # 建物名
        data_home["name"]=estate.find(class_='cassetteitem_content-title').text
        # 住所
        data_home["address"]=estate.find(class_='cassetteitem_detail-col1').text
        # 最寄り駅のアクセス
        children = estate.find(class_='cassetteitem_detail-col2')
        for id,grandchild in enumerate(children.find_all(class_='cassetteitem_detail-text')):
            data_home["access"]=grandchild.text
        # 築年数と階数
        children = estate.find(class_='cassetteitem_detail-col3')
        for grandchild in children.find_all('div'):
            data_home["status"]=grandchild.text
        
        print(data_home)

        """
        # 部屋情報
        rooms = estate.find(class_='cassetteitem_other')
        for room in rooms.find_all(class_='js-cassette_link'):
            data_room = []
            
            # 部屋情報が入っている表を探索
            for id_, grandchild in enumerate(room.find_all('td')):
                # 階
                if id_ == 2:
                    data_room.append(grandchild.text.strip())
                # 家賃と管理費
                elif id_ == 3:
                    data_room.append(grandchild.find(class_='cassetteitem_other-emphasis ui-text--bold').text)
                    data_room.append(grandchild.find(class_='cassetteitem_price cassetteitem_price--administration').text)
                # 敷金と礼金
                elif id_ == 4:
                    data_room.append(grandchild.find(class_='cassetteitem_price cassetteitem_price--deposit').text)
                    data_room.append(grandchild.find(class_='cassetteitem_price cassetteitem_price--gratuity').text)
                # 間取りと面積
                elif id_ == 5:
                    data_room.append(grandchild.find(class_='cassetteitem_madori').text)
                    data_room.append(grandchild.find(class_='cassetteitem_menseki').text)
                # url
                elif id_ == 8:
                    get_url = grandchild.find(class_='js-cassette_link_href cassetteitem_other-linktext').get('href')
                    abs_url = urllib.parse.urljoin(url,get_url)
                    data_room.append(abs_url)
            # 物件情報と部屋情報をくっつける
            data_sample = data_home + data_room
            data_samples.append(data_sample)
        """
        
    # 1アクセスごとに1秒休む
    time.sleep(1)
    
    # 進捗確認
    # このページの作業時間を表示
    after = time.time()
    running_time = after - before
    times.append(running_time)
    print(f'{page}ページ目：{running_time}秒')
    # 取得した件数
    print(f'総取得件数：{len(data_samples)}')
    # 作業進捗
    complete_ratio = round(page/max_page*100,3)
    print(f'完了：{complete_ratio}%')
    # 作業の残り時間目安を表示
    running_mean = np.mean(times)
    running_required_time = running_mean * (max_page - page)
    hour = int(running_required_time/3600)
    minute = int((running_required_time%3600)/60)
    second = int(running_required_time%60)
    print(f'残り時間：{hour}時間{minute}分{second}秒\n')


# 処理時間を測りたい
finish = time.time()
running_all = finish - start
print('総経過時間：',running_all)
