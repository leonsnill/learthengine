import ee


def ndvi(img):
       ndvi = img.normalizedDifference(['NIR', 'R']).rename('NDVI')
       #ndvi = ndvi.multiply(10000)
       return img.addBands(ndvi)


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


def ndwi1(img):
       ndwi = img.normalizedDifference(['NIR', 'SWIR1']).rename('NDWI1')
       #ndwi = ndwi.multiply(10000)
       return img.addBands(ndwi)


def ndwi2(img):
       ndwi = img.normalizedDifference(['G', 'NIR']).rename('NDWI2')
       #ndwi = ndwi.multiply(10000)
       return img.addBands(ndwi)


# Zha et al. (2003): Use of Normalized Difference Built-Up Index in Automatically Mapping Urban Areas from TM Imagery
def ndbi(img):
    ndbi = img.normalizedDifference(['SWIR1', 'NIR']).rename('NDBI')
    # ndwi = ndwi.multiply(10000)
    return img.addBands(ndbi)


# Tasseled Cap Transformation (brightness, greenness, wetness) based on Christ 1985
def tcg(img):
    tcg = img.expression(
                         'B*(-0.1603) + G*(-0.2819) + R*(-0.4934) + NIR*0.7940 + SWIR1*(-0.0002) + SWIR2*(-0.1446)',
                         {
                         'B': img.select(['B']),
                         'G': img.select(['G']),
                         'R': img.select(['R']),
                         'NIR': img.select(['NIR']),
                         'SWIR1': img.select(['SWIR1']),
                         'SWIR2': img.select(['SWIR2'])
                         }).rename('TCG')
    #tcg = tcg.multiply(10000)
    return img.addBands(tcg)


def tcb(img):
    tcb = img.expression(
                         'B*0.2043 + G*0.4158 + R*0.5524 + NIR*0.5741 + SWIR1*0.3124 + SWIR2*0.2303',
                         {
                         'B': img.select(['B']),
                         'G': img.select(['G']),
                         'R': img.select(['R']),
                         'NIR': img.select(['NIR']),
                         'SWIR1': img.select(['SWIR1']),
                         'SWIR2': img.select(['SWIR2'])
                         }).rename('TCB')
    #tcb = tcb.multiply(10000)
    return img.addBands(tcb)


def tcw(img):
       tcw = img.expression(
              'B*0.0315 + G*0.2021 + R*0.3102 + NIR*0.1594 + SWIR1*(-0.6806) + SWIR2*(-0.6109)',
              {
                     'B': img.select(['B']),
                     'G': img.select(['G']),
                     'R': img.select(['R']),
                     'NIR': img.select(['NIR']),
                     'SWIR1': img.select(['SWIR1']),
                     'SWIR2': img.select(['SWIR2'])
              }).rename('TCW')
       #tcw = tcw.multiply(10000)
       return img.addBands(tcw)