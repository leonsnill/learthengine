import ee


def atmospheric_functions(cs=None, sensor='L5'):

    if cs is None:
        cs_l8 = [0.04019, 0.02916, 1.01523,
                 -0.38333, -1.50294, 0.20324,
                 0.00918, 1.36072, -0.27514]
        cs_l7 = [0.06518, 0.00683, 1.02717,
                 -0.53003, -1.25866, 0.10490,
                 -0.01965, 1.36947, -0.24310]
        cs_l5 = [0.07518, -0.00492, 1.03189,
                 -0.59600, -1.22554, 0.08104,
                 -0.02767, 1.43740, -0.25844]

        if sensor == 'L5':
            cs = cs_l5
        elif sensor == 'L7':
            cs = cs_l7
        elif sensor == 'L8':
            cs = cs_l8
        else:
            return

    def wrap(img):
        af1 = img.expression(
            '('+str(cs[0])+'*(WV**2))+('+str(cs[1])+'*WV)+('+str(cs[2])+')',
            {
                'WV': img.select('WV_SCALED')
            }
        ).rename('AF1')

        af2 = img.expression(
            '(' + str(cs[3]) + '*(WV**2))+(' + str(cs[4]) + '*WV)+(' + str(cs[5]) + ')',
            {
                'WV': img.select('WV_SCALED')
            }
        ).rename('AF2')

        af3 = img.expression(
            '(' + str(cs[6]) + '*(WV**2))+(' + str(cs[7]) + '*WV)+(' + str(cs[8]) + ')',
            {
                'WV': img.select('WV_SCALED')
            }
        ).rename('AF3')

        return img.addBands(af1).addBands(af2).addBands(af3)
    return wrap


def scale_wv(img):
    wv_scaled = ee.Image(img.get('WV')).multiply(0.1).rename('WV_SCALED')
    wv_scaled = wv_scaled.resample('bilinear')
    return img.addBands(wv_scaled)


def radcal(img):
    radiance = ee.Algorithms.Landsat.calibratedRadiance(img).rename('RADIANCE')
    return img.addBands(radiance)


# L to ee.Image
def radiance_addband(img):
    l = ee.Image(img.get('L')).select('RADIANCE').rename('L')
    return img.addBands(l)


def add_wv(imgcol, wv_list):
    array = ee.Array(wv_list)
    list = imgcol.toList(imgcol.size()).zip(array.toList())
    return ee.ImageCollection(list.map(lambda x: ee.Image(ee.List(x).get(0)).set('WV', ee.List(x).get(1))))


from datetime import datetime, timedelta
import numpy as np
import cdsapi
import gdal


def era5_tcwv(imgcol, roi=None):

    # prepare imgcol
    imgcol = imgcol.sort("system:time_start")
    unix_time = imgcol.reduceColumns(ee.Reducer.toList(), ["system:time_start"]).get('list').getInfo()


    def hour_rounder(t):
        return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
                + timedelta(hours=t.minute // 30))


    time = [hour_rounder(datetime.fromtimestamp(x / 1000)) for x in unix_time]
    dates = [x.strftime('%Y-%m-%d') for x in time]
    hour = [time[0].strftime('%H:%M')]

    x, y = np.unique(np.array(dates), return_inverse=True)
    c = cdsapi.Client()
    c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'format': 'grib',
            'variable': 'total_column_water_vapour',
            "date": dates,
            'time': hour,
            'area': roi,  # N W S E
        },
        'era5_tcwv.grib')

    # get wv raster imfo
    wv = gdal.Open('era5_tcwv.grib')
    gt = wv.GetGeoTransform()
    gt = [round(x, 4) for x in gt]

    # client side arrays
    wv_array = wv.ReadAsArray()
    wv_array = np.round(wv_array * 0.1, 5)  # scale from kg/m2 to
    wv_array = [wv_array[i] for i in y]  # needed because of unique dates

    # create list of server-side images
    wv_imgs = [ee.Image(ee.Array(x.tolist())).setDefaultProjection(crs='EPSG:4326', crsTransform=gt) for x in wv_array]
    wv_imgs = [wv_imgs[i].rename('WV_SCALED').set('system:time_start', unix_time[i]) for i in range(len(unix_time))]
    wv_img_list = ee.List(wv_imgs)
    imgcol_wv = ee.ImageCollection(wv_img_list)

    filterTimeEq = ee.Filter.equals(
        leftField='system:time_start',
        rightField='system:time_start'
    )

    join_era5 = ee.Join.saveFirst(
        matchKey='WV_SCALED',
        ordering='system:time_start'
    )

    imgcol = ee.ImageCollection(join_era5.apply(imgcol, imgcol_wv, filterTimeEq))

    def wv_addband(img):
        #wv_scaled = ee.Image(img.get('WV_SCALED')).multiply(0.1).rename('WV_SCALED')
        #wv_scaled = wv_scaled.resample('bilinear')
        return img.addBands(ee.Image(img.get('WV_SCALED')))

    imgcol = imgcol.map(wv_addband)

    def add_wv_img(imgcol, wv_img_list):
        wv_img_list = ee.List(wv_img_list)
        list = imgcol.toList(imgcol.size()).zip(wv_img_list)
        list = list.map(lambda x: ee.Image(ee.List(x).get(0)) \
                        .addBands(ee.Image(ee.List(x).get(1)).rename('WV_SCALED')))
        return ee.ImageCollection(list)

    #imgcol = add_wv_img(imgcol, wv_imgs)

    return imgcol
