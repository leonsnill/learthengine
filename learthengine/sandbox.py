import ee
ee.Initialize()
from learthengine import composite

feno = [25.209, 69.377, 26.943, 69.795]
prolif = [56.931, 66.873, 58.760, 67.5421]
wc = [17.425, -35.082, 24.940, -30.285]
ct = [17, -35, 21, -32]
sa = [15.291, -35.207, 33.748, -21.878]
charp = [65.736, 66.682, 66.364, 66.882]
yarsk = [67.927, 67.090, 68.303, 67.178]

kwargs = {
    'sensor': 'LS',
    'bands': ['CLOUD_DISTANCE'],  # ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']  ['TCB', 'TCG', 'TCW']
    'pixel_resolution': 30,
    'cloud_cover': 50,
    'masks': ['cloud', 'cshadow', 'snow'],  # 'cloud', 'cshadow', 'snow'
    #'masks': [],
    'T_threshold': None,
    'T_omission': False,
    'roi': yarsk,  # 38.4824, 8.7550, 39.0482, 9.2000 Addis
    'score': 'STM',
    'min_clouddistance': 10,
    'max_clouddistance': 80,
    'reducer': ee.Reducer.median(), #ee.Reducer.intervalMean(10, 90),
    'target_years': [2018],  # 1985, 1990, 1995, 2000, 2010, 2015, 2020
    'surr_years': 2,
    'target_doys': [166, 258],  # [16, 46, 75, 105, 136, 166, 197, 228, 258, 289, 319, 350]
    'doy_range': 15,
    'doy_vs_year': 60,
    'exclude_slc_off': True,
    'export_option': 'Drive',
    'asset_path': "users/leonxnill/Addis/",
    'export_name': 'CD_YARSK_VIR',
    'lst_threshold': 5,
    'wv_method': 'NCEP',
    'mask_percentiles': False,
    'buffer_clouds': True
    #'epsg': 'EPSG:22293'
}

composite.img_composite(**kwargs)

# [-18.675, -37.455, 52.867, 38.463] Africa
# [37.066,9.304, 38.138,10.013] Ethiopia Highland Example

# pip install --upgrade git+https://github.com/leonsnill/learthengine.git


import ee
ee.Initialize()

kwargs = {
    'sensor': 'S2_L2A',
    'bands': ['EVI'],  # ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']
    'pixel_resolution': 10,
    'years': [2019, 2020],
    'months': list(range(5, 9)),
    'cloud_cover': 70,
    'masks': ['cloud', 'cshadow', 'snow'],
    'roi': charp,  # 38.4824, 8.7550, 39.0482, 9.2000 Addis
    'exclude_slc_off': False,
    'export_option': 'Drive',
    'export_name': 'CHARP',
    'lst_threshold': None,
    'wv_method': 'NCEP'
}

from learthengine import composite

composite.img_layerstack(**kwargs)

























import ee
ee.Initialize()

sensor='LS'
bands = ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']
pixel_resolution = 30
cloud_cover=50
masks=['cloud', 'cshadow', 'snow']
roi=[102.92, 21.43, 103.22, 21.16]
score = "STM"
reducer=ee.Reducer.percentile([90])
target_years=[2002]
surr_years=0
target_doys=[183]
doy_range=365
epsg=None
doy_vs_year=20
min_clouddistance=10
max_clouddistance=50
weight_doy=0.4
weight_year=0.4
weight_cloud=0.2
exclude_slc_off=True
export_option="Drive"
asset_path="users/leonxnill/Addis/"
export_name='LST_MED_ADDIS_1995'
lst_threshold=10
wv_method="ERA5"




aoi = ee.Geometry.Polygon(
  [[[39.65168701191035, 7.7878201025696665],
    [39.859428738148814, 7.757394203339766],
    [39.859428738148814, 7.7878201025696665]]])

# Get 2-d pixel array for AOI - returns feature with 2-D pixel array as property per band.
band_arrs = first.sampleRectangle(region=ee.Geometry.Rectangle(roi))

# Get individual band arrays.
band_arr_b4 = band_arrs.get('WV_SCALED')
band_arr_b5 = band_arrs.get('B5')
band_arr_b6 = band_arrs.get('B6')

# Transfer the arrays from server to client and cast as np array.
np_arr_b4 = np.array(band_arr_b4.getInfo())
np_arr_b5 = np.array(band_arr_b5.getInfo())
np_arr_b6 = np.array(band_arr_b6.getInfo())




from datetime import datetime, timedelta
import numpy as np
import cdsapi
import gdal

roi = [roi[1] - 0.5, roi[0] + 0.5, roi[3] + 0.5, roi[2] - 0.5]

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
            'area': roi,
        },
        'era5_tcwv.grib')

    # get wv raster imfo
    wv = gdal.Open('era5_tcwv.grib')
    gt = wv.GetGeoTransform()

    # client side arrays
    wv_array = wv.ReadAsArray()
    wv_array = [wv_array[i] for i in y]  # needed because of unique dates

    # create list of server-side images
    wv_imgs = [ee.Image(ee.Array(x.tolist())).setDefaultProjection(crs='EPSG:4326', crsTransform=gt) for x in wv_array]


    def add_wv_img(imgcol, wv_img_list):
        wv_img_list = ee.List(wv_img_list)
        list = imgcol.toList(imgcol.size()).zip(wv_img_list)
        list = list.map(lambda x: ee.Image(ee.List(x).get(0)) \
                        .addBands(ee.Image(ee.List(x).get(1)).rename('WV')))
        return ee.ImageCollection(list)


    imgcol = add_wv_img(imgcol, wv_imgs)
    return imgcol



# get time in milliseconds
imgCol_L5_SR = imgCol_L5_SR.sort("system:time_start")
unix_time = imgCol_L5_SR.reduceColumns(ee.Reducer.toList(), ["system:time_start"]).get('list').getInfo()
from datetime import datetime, timedelta

def hour_rounder(t):
    return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
               +timedelta(hours=t.minute//30))

time = [hour_rounder(datetime.fromtimestamp(x/1000)) for x in unix_time]
dates = [x.strftime('%Y-%m-%d') for x in time]
hour = [time[0].strftime('%H:%M')]

roi = [38.4824, 8.7550, 39.0482, 9.2000]


a = np.array(dates)
x,y = np.unique(a, return_inverse = True)


c = cdsapi.Client()
c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'format': 'grib',
        'variable': 'total_column_water_vapour',
        "date": dates,
        'time': hour,
        'area': [roi[1]-1, roi[0]+1, roi[3]+1, roi[2]-1],
    },
    'download.grib')


# get wv raster imfo
wv = gdal.Open("download.grib")
gt = wv.GetGeoTransform()

# client side arrays
wv_array = wv.ReadAsArray()#.flatten().tolist()
wv_array = [wv_array[i] for i in y]  # needed because of unique dates

# create list of server-side images
wv_imgs = [ee.Image(ee.Array(x.tolist())).setDefaultProjection(crs='EPSG:4326', crsTransform=gt) for x in wv_array]

#wv_array_i = wv_array[0]
#ea = ee.Array(wv_array_i.tolist())
#eai = ee.Image(ea).setDefaultProjection(crs='EPSG:4326', crsTransform=gt)


def add_wv_img(imgcol, wv_img_list):
    wv_img_list = ee.List(wv_img_list)
    list = imgcol.toList(imgcol.size()).zip(wv_img_list)
    list = list.map(lambda x: ee.Image(ee.List(x).get(0)) \
                    .addBands(ee.Image(ee.List(x).get(1)).rename('WV')))
    return ee.ImageCollection(list)


def add_wv_point(imgcol, wv_list):
    array = ee.Array(wv_list)
    list = imgcol.toList(imgcol.size()).zip(array.toList())
    return ee.ImageCollection(list.map(lambda x: ee.Image(ee.List(x).get(0)).set('WV', ee.List(x).get(1))))

test = add_wv_img(imgCol_L5_SR, wv_imgs)
first = test.first().select('WV')

# add wv as band
def add_wv_band(img):
    wv = ee.Image.constant(ee.Number(img.get('WV'))).rename('WV')
    return img.addBands(wv)

test2 = test.map(add_wv_band)

first = test2.first().select('WV')
