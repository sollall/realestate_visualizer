from .utils import get_lat_lon

def transform(data):
    
    lons,lats=get_lat_lon(data["address"].values)
    data["lons"]=lons
    data["lats"]=lats

    return data