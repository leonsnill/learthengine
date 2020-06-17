import ee


def add_timeband(start_date='1970-01-01', diff_type='day'):
    def wrap(img):
        img_date = ee.Date(img.get('system:time_start'))
        days = img_date.difference(ee.Date(start_date), diff_type)
        return img.addBands(ee.Image(days).float().rename('TIME'))
    return wrap

