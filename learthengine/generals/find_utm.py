

def find_utm(lon):
    try:
        coords = lon.getInfo().get('coordinates')
        lon = coords[0][0][0]
    except Exception:
        pass
    utm = round((lon + 180) / 6)
    utm = "{0:0=2d}".format(utm)
    return "EPSG:326"+utm

