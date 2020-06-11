

def lst(img):
    lst = img.expression(
        '(GAMMA*(((1/EPSILON)*(AF1*L+AF2))+AF3)+DELTA)-273.15',
        {
            'GAMMA': img.select('GAMMA'),
            'DELTA': img.select('DELTA'),
            'EPSILON': img.select('EPSILON'),
            'AF1': img.select('AF1'),
            'AF2': img.select('AF2'),
            'AF3': img.select('AF3'),
            'L': img.select('L')
        }
    ).rename('LST')
    return img.addBands(lst)


# Gamma Functions
def gamma(coef):
    """ coef L8=1324, L7=1277, L5=1256 """
    def wrap(img):
        gamma = img.expression('(BT**2)/('+str(coef)+'*L)',
                               {'BT': img.select('TIR'),
                                'L': img.select('L')
                                }).rename('GAMMA')
        return img.addBands(gamma)
    return wrap


def delta(coef):
    """ coef L8=1324, L7=1277, L5=1256 """
    def wrap(img):
        delta = img.expression('BT-((BT**2)/'+str(coef)+')',
                               {'BT': img.select('TIR')
                                }).rename('DELTA')
        return img.addBands(delta)
    return wrap


def mask_lst(threshold):
    def wrap(img):
        mask = img.select('LST').gt(threshold)
        return img.updateMask(mask)\
            .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap

