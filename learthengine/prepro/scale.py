

def scale_img(factor, bands, keep=None):
    if keep:
        def wrap(img):
            return img.select(keep).addBands(img.select(bands).toFloat().multiply(factor)\
                                .copyProperties(source=img).set('system:time_start', img.get('system:time_start')))
    else:
        def wrap(img):
            return img.select(bands).toFloat().multiply(factor)\
                                .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap

