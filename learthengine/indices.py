import ee


indices = {
    'ND': '(y-x)/(y+x)'
}

indices_keys = indices.keys()


def index_calculator(img, index, img_params, additional_params=None, band_name=None):
    """

    :param img:
    :param index:
    :param img_params:
    :param additional_params:
    :param band_name:
    :return:
    """
    if index not in indices:
        raise ValueError('Index not defined')

    if not band_name:
        band_name = index

    additional_params = additional_params if additional_params else {}

    index_formula = indices[index]

    expression = {
        key: img.select([band]) for key, band in img_params.items()
    }
    expression.update(additional_params)

    index_img = img.expression(index_formula, expression).rename(band_name)

    return index_img


def normdiff(index, y_band, x_band, band_name='NDVI', add_band=True):
    """

    :param img:
    :param y_band:
    :param x_band:
    :param band_name:
    :return:
    """
    def wrap(img):
        if add_band:
            return img.addBands(index_calculator(img, index, {'y': y_band, 'x': x_band}, band_name=band_name))
        else:
            return index_calculator(img, index, {'y': y_band, 'x': x_band}, band_name=band_name)

    return wrap


ee.Initialize()
ROI = ee.Geometry.Rectangle([8.501, 10.470, 10.701, 8.287])
test = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR').filterBounds(ROI)

test = test.map(normdiff('ND', 'B4', 'B3'))
info = test.getInfo()


test = test.map(lambda img: img.addBands(normdiff(img, 'ND', 'B4', 'B3')))




