from ..core.utils import get_lat_lon

def transform(data):

    data["坪単価"] = data["price"] / 10000 / data["area"] * 3.306

    lons,lats=get_lat_lon(data["address"].values)
    data["lons"]=lons
    data["lats"]=lats

    return data
