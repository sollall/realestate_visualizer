"""外部サイト・外部APIへのアクセスのみを担うIF層のユーティリティ。"""

from retry import retry
import requests
import urllib

# リクエストがうまく行かないパターンを回避するためのやり直し
@retry(tries=3, delay=10, backoff=2)
def load_page(url):
    html = requests.get(url)
    return html

def search_address(address):
    makeUrl = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
    s_quote = urllib.parse.quote(address)
    response=load_page(makeUrl + s_quote)

    try:
        results=response.json()
    except ValueError:
        # レート制限等でJSON以外(HTMLエラーページ等)が返ってきた場合は座標なし扱いにする
        # (requests.exceptions.JSONDecodeErrorはjson.JSONDecodeError経由でValueErrorのサブクラス)
        return None,None

    if not results:
        # 該当する住所が見つからなかった場合も座標なし扱いにする
        return None,None

    lon,lat=results[0]["geometry"]["coordinates"]
    return lon,lat
