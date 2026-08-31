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
    lon,lat=response.json()[0]["geometry"]["coordinates"]
    return lon,lat
