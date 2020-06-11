

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
        epsilon = epsilon.where(img.expression('ndwi2 > 0.1',
                                       {'ndwi2': img.select('NDWI2')}), epsilon_water).rename('EPSILON')

        return img.addBands(epsilon)
    return wrap

