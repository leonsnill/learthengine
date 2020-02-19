

def scale_img(factor):
    def wrap(img):
        return img.toFloat().multiply(factor)\
            .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap

