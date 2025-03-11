#utilsじゃなくてcommon.pyを別で作ってもいいかも
import numpy as np
from retry import retry
import requests
import multiprocessing
from multiprocessing import Pool
from tqdm import tqdm
import urllib

def sigmoid(x, gain=1, offset_x=0):
    return ((np.tanh(((x+offset_x)*gain)/2)+1)/2)

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

def get_lat_lon(addresses):

    LEN_ADDRESSES=len(addresses)
    lons=[]
    lats=[]
    with Pool(processes=multiprocessing.cpu_count()) as pool:
        with tqdm(total=LEN_ADDRESSES) as pbar:
            for result in pool.imap(search_address, addresses):
                lons.append(result[0])
                lats.append(result[1])
                pbar.update(1)
    
    return lons,lats