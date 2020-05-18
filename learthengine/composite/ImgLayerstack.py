import ee
ee.Initialize()
from learthengine import prepro
from learthengine import generals


SENSOR = 'SL'
BANDS = ['NDVI']
PIXEL_RESOLUTION = 10
YEAR_MIN, YEAR_MAX = 2019, 2019
MONTH_MIN, MONTH_MAX = 3, 11
CLOUD_COVER = 60
MASKS = ['cloud', 'cshadow', 'snow']  # only for Landsat
ROI = ee.Geometry.Rectangle([9.1552,9.1258, 9.6036,9.6312])
ROI_NAME = 'NIGERIA'
EPSG = 'UTM'  # UTM for automatic UTM Zone WGS84


# Functions
def layerstack(imgCol):
    # Create initial image
    first = ee.Image(imgCol.first())
    # Write a function that appends a band to an image
    def addband(img, previous):
        datestring = ee.String(img.date().format("YYYY-MM-dd"))
        sensorstring = ee.String(img.get('satellite_id'))
        namestring = ee.String(sensorstring).cat(datestring)
        return ee.Image(previous).addBands(img.rename(namestring))
    return ee.Image(imgCol.iterate(addband, first))


def get_dates(imgCol):
    def wrap(img):
        return ee.Date(ee.Image(img).date().format("YYYY-MM-dd"))
    return ee.List(imgCol.toList(imgCol.size()).map(wrap))


def mosaic(imgCol, date):
    def wrap(date, newList):
        # cast
        newList = ee.List(newList)
        date = ee.Date(date)

        # filter collection
        filtered = ee.ImageCollection(imgCol.filterDate(date, date.advance(1, 'day')))

        # mosaic
        first = filtered.first()
        mosaic = ee.Image(filtered.mosaic())\
            .copyProperties(source=first).set('system:time_start', first.get('system:time_start'))

        return ee.List(newList.add(mosaic))

    return ee.ImageCollection(ee.List(date.iterate(wrap, ee.List([]))))



# select bits for mask
dict_mask = {'cloud': ee.Number(2).pow(5).int(),
             'cshadow': ee.Number(2).pow(3).int(),
             'snow': ee.Number(2).pow(4).int()}

sel_masks = [dict_mask[x] for x in MASKS]
bits = ee.Number(1)

for m in sel_masks:
    bits = ee.Number(bits.add(m))

imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
    .filterBounds(ROI) \
    .filter(ee.Filter.calendarRange(YEAR_MIN, YEAR_MAX, 'year')) \
    .filter(ee.Filter.calendarRange(MONTH_MIN, MONTH_MAX, 'month')) \
    .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
    .map(prepro.rename_bands_l5) \
    .map(prepro.mask_landsat_sr(bits)) \
    .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR']))\
    .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

imgCol_L7_SR = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
    .filterBounds(ROI) \
    .filter(ee.Filter.calendarRange(YEAR_MIN, YEAR_MAX, 'year')) \
    .filter(ee.Filter.calendarRange(MONTH_MIN, MONTH_MAX, 'month')) \
    .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
    .map(prepro.rename_bands_l7) \
    .map(prepro.mask_landsat_sr(bits)) \
    .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
    .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

imgCol_L8_SR = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR') \
    .filterBounds(ROI) \
    .filter(ee.Filter.calendarRange(YEAR_MIN, YEAR_MAX, 'year')) \
    .filter(ee.Filter.calendarRange(MONTH_MIN, MONTH_MAX, 'month')) \
    .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
    .map(prepro.rename_bands_l8) \
    .map(prepro.mask_landsat_sr(bits)) \
    .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR']))\
    .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterBounds(ROI) \
    .filter(ee.Filter.calendarRange(YEAR_MIN, YEAR_MAX, 'year')) \
    .filter(ee.Filter.calendarRange(MONTH_MIN, MONTH_MAX, 'month')) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER)) \
    .map(prepro.mask_s2_cdi(-0.5)) \
    .map(prepro.rename_bands_s2) \
    .map(prepro.mask_s2_scl) \
    .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))


# --------------------------------------------------
# MERGE imgCols
# --------------------------------------------------
if SENSOR == 'S2_SR':
    imgCol_SR = imgCol_S2_L2A
elif SENSOR == 'LS':
    imgCol_SR = imgCol_L5_SR.merge(imgCol_L7_SR).merge(imgCol_L8_SR)
    imgCol_SR = imgCol_SR.sort("system:time_start")
elif SENSOR == 'L8':
    imgCol_SR = imgCol_L8_SR
elif SENSOR == 'L7':
    imgCol_SR = imgCol_L7_SR
elif SENSOR == 'L5':
    imgCol_SR = imgCol_L5_SR
elif SENSOR == 'SL8':
    imgCol_SR = imgCol_L8_SR.merge(imgCol_S2_L2A)
elif SENSOR == 'SL':
    imgCol_SR = imgCol_L5_SR.merge(imgCol_L7_SR).merge(imgCol_L8_SR).merge(imgCol_S2_L2A)
else:
    imgCol_SR = None
    print('False SENSOR selection')

imgCol_SR = imgCol_SR.map(prepro.ndvi)
imgCol_SR = imgCol_SR.map(prepro.ndwi1)
imgCol_SR = imgCol_SR.map(prepro.ndwi2)
imgCol_SR = imgCol_SR.map(prepro.tcg)
imgCol_SR = imgCol_SR.map(prepro.tcb)
imgCol_SR = imgCol_SR.map(prepro.tcw)

imgCol_SR = imgCol_SR.sort("system:time_start")

dates = get_dates(imgCol_SR)
range = dates.distinct()
newcol = mosaic(imgCol_SR.select(BANDS), range)  # select to avoid incompabilities with two imgCols (e.g. Red Edge)


# find epsg
if EPSG == 'UTM':
    EPSG = generals.find_utm(ROI)


for band in BANDS:
    lyr = layerstack(newcol.select(band))

    lyr = lyr.multiply(10000)
    lyr = lyr.toInt16()

    out_file = SENSOR + '_layerstack_' + ROI_NAME + '_' + band + '_' + str(YEAR_MIN) + '-' + str(YEAR_MAX) + \
               '_' + str(MONTH_MIN) + '-' + str(MONTH_MAX)

    out = ee.batch.Export.image.toDrive(image=lyr, description=out_file,
                                        scale=PIXEL_RESOLUTION,
                                        maxPixels=1e13,
                                        region=ROI['coordinates'][0],
                                        crs=EPSG)
    process = ee.batch.Task.start(out)

