from bs4 import BeautifulSoup
from multiprocessing import Pool
from tqdm import tqdm

from .utils import load_page

def fetch_soup(url):
    html = load_page(url)
    return BeautifulSoup(html.content, 'html.parser')

def get_max_pages(soup, css_selector):
    return int(soup.select(css_selector)[-1].get_text(strip=True))

def scrape_paginated(url_format, max_pages, parse_page, processes=8, start_page=1):
    results_all = []
    with Pool(processes=processes) as pool:
        with tqdm(total=max_pages - start_page) as pbar:
            urls = [url_format.format(num) for num in range(start_page, max_pages)]
            for result in pool.imap(parse_page, urls):
                results_all.extend(result)
                pbar.update(1)

    return results_all
