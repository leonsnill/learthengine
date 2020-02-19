import ee

ee.Initialize()
ROI = ee.Geometry.Rectangle([8.501, 10.470, 10.701, 8.287])
test = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR').filterBounds(ROI)


# Scale Class
class Scale(object):
    def __init__(self, scale=0.0001):
        self.scale = scale

    def f_scale(self, img):
        imgs_to_scale = img.select(['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']).multiply(self.scale).float()
        imgs_to_append = img.select(['pixel_qa'])
        imgs = imgs_to_scale.addBands(imgs_to_append) \
            .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
        return imgs

    def map(self, imgcol):
        imgcol = imgcol.map(self.f_scale)
        return imgcol




# PBC class
class PBC(object):
    def __init__(self, imgcol=None, masks=None, scale=None, reducer=None):
        self._imgcol = imgcol
        self._id = imgcol.getInfo()['id'].split("/")[1:4:2]
        self._masks = masks
        self._scale = scale
        self._reducer = reducer


    def rename_bands(self):
        new_bands = ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2', 'QA']
        if self._id[0] == 'LC08':
            bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'pixel_qa']
        self._imgcol = self._imgcol.select(bands).rename(new_bands)


    def scale(self):
        self._imgcol = self._scale.map(self._imgcol)










