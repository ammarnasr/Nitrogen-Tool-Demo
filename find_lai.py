from sentinelhub import (MimeType, CRS, BBox, SentinelHubRequest, DataCollection, bbox_to_dimensions)
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from sentinelhub import  SHConfig
import requests
from sklearn.cluster import KMeans
import rioxarray as rx
import geopandas as gpd



config = SHConfig()
config.instance_id      = "68954d9b-19c5-4e45-b6a0-2295f0484780"
config.sh_client_id     = "be6663e2-fbab-41ba-bfa5-34acb0db354d"
config.sh_client_secret = "Qt</7X~RRT+|f&hBL]aIy_i>n*hLUoK{3J5_!8xV"

with open('./lai.js') as f:
    evalscript_lai = f.read()

def get_lai(gdf,date=None, evalscript=evalscript_lai, config=config, data_source = DataCollection.SENTINEL2_L1C, identifier ='default', mime_type = MimeType.TIFF, dir_path='./', save=False):
    
    if date == None:
        ds = get_dates(gdf)
        print(ds)
        date = ds[0]
    bbox, bbox_size = get_bbox(gdf)
    input_data = SentinelHubRequest.input_data(data_collection= data_source, time_interval=(date, date))
    output_data = SentinelHubRequest.output_response(identifier, mime_type)
    request = SentinelHubRequest(
            data_folder=dir_path,
            evalscript=evalscript,
            input_data=[input_data],
            responses=[output_data],
            bbox=bbox,
            size=bbox_size,
            config=config,
            )
    return request.get_data(save_data=save, redownload=False)
    
    
def get_token(config=config):
    client_id = config.sh_client_id
    client_secret = config.sh_client_secret
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(token_url='https://services.sentinel-hub.com/oauth/token',client_secret=client_secret)
    return token['access_token']

def get_bbox(gdf, resolution = 10):
    bbox = gdf.bounds
    r = bbox.iloc[0]
    bbox = [r.minx, r.miny, r.maxx, r.maxy]
    bbox = BBox(bbox=bbox, crs=CRS.WGS84)
    bbox_size = bbox_to_dimensions(bbox, resolution=resolution)
    return bbox, bbox_size

def get_dates(gdf, year = 2022, bbox=None):
    token = get_token()
    if bbox==None:
        r = gdf.bounds.iloc[0]
        bbox = [r.minx, r.miny, r.maxx, r.maxy]
    headers = {'Content-Type': 'application/json','Authorization': 'Bearer '+ token}
    interval = f'{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z'
    data = f'{{ "collections": [ "sentinel-2-l2a" ], "datetime": "{interval}", "bbox": {bbox}, "limit": 100, "distinct": "date" }}'
    response = requests.post('https://services.sentinel-hub.com/api/v1/catalog/search', headers=headers, data=data)
    return response.json()['features']

def get_gdf(path, gdf):
    im = rx.open_rasterio(path)
    gdf = gdf.iloc[0:1]
    im = im.rio.clip(gdf.geometry, gdf.crs, drop=True, invert=False)
    df_lai = im.to_dataframe('LAI').dropna(subset=['LAI']).reset_index()[['y','x','LAI']]
    gdf_lai = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_xy(df_lai['x'], df_lai['y'], crs=im.rio.crs))
    gdf_lai['LAI'] = df_lai['LAI']
    return gdf_lai



def get_clustered(gdf_lai):
    km = KMeans(n_clusters=4, max_iter=200).fit(gdf_lai[['LAI']])
    gdf_lai['LAI_Clusters'] = [km.cluster_centers_[i].item() for i in km.predict(gdf_lai[['LAI']])]
    return gdf_lai, km

