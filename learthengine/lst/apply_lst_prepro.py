import ee
from .atmospheric_functions import atmospheric_functions, radiance_addband, scale_wv
from .collection_matching import maxDiffFilter, join_wv
from .land_surface_temperatue import delta, gamma


def apply_lst_prepro(imgcol_l5, imgcol_l7, imgcol_l8):

    imgcol_l5 = imgcol_l5.map(radiance_addband)
    imgcol_l7 = imgcol_l7.map(radiance_addband)
    imgcol_l8 = imgcol_l8.map(radiance_addband)

    # Atmospheric Functions
    imgcol_l5 = imgcol_l5.map(atmospheric_functions(sensor='L5'))
    imgcol_l7 = imgcol_l7.map(atmospheric_functions(sensor='L7'))
    imgcol_l8 = imgcol_l8.map(atmospheric_functions(sensor='L8'))

    # Delta and Gamma Functions
    imgcol_l5 = imgcol_l5.map(delta(1256))
    imgcol_l7 = imgcol_l7.map(delta(1277))
    imgcol_l8 = imgcol_l8.map(delta(1324))

    imgcol_l5 = imgcol_l5.map(gamma(1256))
    imgcol_l7 = imgcol_l7.map(gamma(1277))
    imgcol_l8 = imgcol_l8.map(gamma(1324))

    return imgcol_l5, imgcol_l7, imgcol_l8

