import ee
ee.Initialize()

kwargs = {
    'sensor': 'LS',
    'bands': ['LST'],  # ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']
    'pixel_resolution': 30,
    'cloud_cover': 70,
    'masks': ['cloud', 'cshadow', 'snow'],
    'roi': [38.4824, 8.7550, 39.0482, 9.2000],  # 38.4824, 8.7550, 39.0482, 9.2000 Addis
    'score': 'STM',
    'reducer': ee.Reducer.percentile([90]),
    'target_years': [1995],  # 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020
    'surr_years': 1,
    'target_doys': [182],  # [16, 46, 75, 105, 136, 166, 197, 228, 258, 289, 319, 350]
    'doy_range': 182,
    'exclude_slc_off': True,
    'export_option': 'Drive',
    'asset_path': "users/leonxnill/Addis/",
    'export_name': 'LST_P90_ADDIS',
    'lst_threshold': 10
}

from learthengine import composite

composite.img_composite(**kwargs)

# [-18.675, -37.455, 52.867, 38.463] Africa
# [37.066,9.304, 38.138,10.013] Ethiopia Highland Example

# pip install --upgrade git+https://github.com/leonsnill/learthengine.git

sensor='L8'
bands = ['lst']
pixel_resolution = 30
cloud_cover=70
masks=['cloud', 'cshadow', 'snow']
roi=[38.4824, 8.7550, 39.0482, 9.2000]
score = "STM"
reducer=ee.Reducer.median()
target_years=[2017]
surr_years=3
target_doys=[182]
doy_range=60
epsg=None
doy_vs_year=20
min_clouddistance=10
max_clouddistance=50
weight_doy=0.4
weight_year=0.4
weight_cloud=0.2
exclude_slc_off=True
export_option="Drive"
asset_path="users/leonxnill/Addis/"
export_name='LST_MED_ADDIS'
lst_threshold=None
