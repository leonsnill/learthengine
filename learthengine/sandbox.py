import ee

kwargs = {
    'sensor': 'L8',
    'bands': ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'],
    'pixel_resolution': 180,
    'cloud_cover': 70,
    'masks': ['cloud', 'cshadow', 'snow'],
    'roi': [-18.675, -37.455, 52.867, 38.463],  # 38.4824, 8.7550, 39.0482, 9.2000 Addis
    'score': 'STM',
    'reducer': ee.Reducer.median(),
    'target_years': [2017],  # 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020
    'surr_years': 3,
    'target_doys': [289],  # [16, 46, 75, 105, 136, 166, 197, 228, 258, 289, 319, 350]
    'doy_range': 30,
    'exclude_slc_off': True,
    'export_option': 'Drive',
    'asset_path': "users/leonxnill/Addis/",
    'export_name': 'VIR_MED_Safrica'
}

import learthengine

learthengine.composite.img_composite(**kwargs)

# [-18.675, -37.455, 52.867, 38.463] Africa
# [37.066,9.304, 38.138,10.013] Ethiopia Highland Example





imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')\
    .filterBounds(select_roi)\
    .filter(ee.Filter.calendarRange(year_start,year_end,'year'))\
    .filter(ee.Filter.calendarRange(month_start,month_end,'month'))\
    .filter(ee.Filter.lt('CLOUD_COVER_LAND', max_cloud_cover))\
    .map(prepro.rename_bands_l5) \
    .map(prepro.mask_landsat_sr(masks)) \
    .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR']))\
    .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

def fvc(ndvi_soil=0.15, ndvi_vegetation=0.9):
    """
    Derive fractional vegetation cover from linear relationship to NDVI
    Default valaues follow recommendations for higher resolution data according to Jimenez-Munoz et al. (2009):
    "Comparison Between Fractional Vegetation Cover Retrievals from Vegetation Indices and Spectral Mixture Analysis:
    Case Study of PROBA/CHRIS Data Over an Agricultural Area", Sensors, 9(2), 768–793.
    """
    def wrap(img):
        fvc = img.expression(
            '((NDVI-NDVI_s)/(NDVI_v-NDVI_s))**2',
            {
                'NDVI': img.select('NDVI'),
                'NDVI_s': ndvi_soil,
                'NDVI_v': ndvi_vegetation
            }
        )
        fvc = fvc.where(fvc.expression('fvc > 1',
                                       {'fvc': fvc}), 1)
        fvc = fvc.where(fvc.expression('fvc < 0',
                                       {'fvc': fvc}), 0).rename('FVC')
        return img.addBands(fvc)
    return wrap

imgCol_L5_SR = imgCol_L5_SR.map(ndwi2)
imgCol_L5_SR = imgCol_L5_SR.map(ndvi)
imgCol_L5_SR = imgCol_L5_SR.map(fvc())
def emissivity(epsilon_soil=0.97, epsilon_vegetation=0.985, epsilon_water=0.99):
    def wrap(img):
        epsilon = img.expression(
            'epsilon_s+(epsilon_v-epsilon_s)*FVC',
            {
                'FVC': img.select('FVC'),
                'epsilon_s': epsilon_soil,
                'epsilon_v': epsilon_vegetation
            }
        )
        epsilon = epsilon.where(img.expression('ndwi2 > 0.234',
                                               {'ndwi2': img.select('NDWI2')}), epsilon_water).rename('EPSILON')

        return img.addBands(epsilon)
    return wrap

imgCol_L5_SR = imgCol_L5_SR.map(emissivity())
test = imgCol_L5_SR.first().select('EPSILON')
test.getInfo()
out = ee.batch.Export.image.toDrive(image=test, description="emmi_final",
                                    scale=30,
                                    maxPixels=1e13,
                                    region=select_roi['coordinates'][0],
                                    crs=epsg)

process = ee.batch.Task.start(out)

















