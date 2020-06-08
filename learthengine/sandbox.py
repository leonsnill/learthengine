kwargs = {
    'sensor': 'S2_L2A',
    'bands': ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'],
    'pixel_resolution': 20,
    'cloud_cover': 70,
    'masks': ['cloud', 'cshadow', 'snow'],
    'roi': [38.4824, 8.7550, 39.0482, 9.2000],
    'score': 'STM',
    'reducer': ee.Reducer.median(),
    'target_years': [2020],  # 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020
    'surr_years': 1,
    'target_doys': [182],  # [16, 46, 75, 105, 136, 166, 197, 228, 258, 289, 319, 350]
    'doy_range': 182,
    'exclude_slc_off': True,
    'export_option': 'Asset',
    'asset_path': "users/leonxnill/Addis/",
    'export_name': 'MEDIAN_ADDIS'
}

from .composite import img_composite

img_composite(**kwargs)