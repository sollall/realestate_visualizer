import multiprocessing
from multiprocessing import Pool
from tqdm import tqdm
from extract.utils import search_address

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