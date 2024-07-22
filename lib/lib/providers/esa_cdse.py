import os
import json
import requests
import pystac
from dateutil.parser import parse

from ..base import geometry as geom_fct
from ..datasets.sentinel import get_scene_id_info, get_scene_id_folder, get_collection_name

def login(username, password):
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    try:
        r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
        )
        r.raise_for_status()
    except Exception as e:
        raise Exception(f"Keycloak token creation failed. Reponse from the server was: {r.json()}")
    return r.json()["access_token"]


def search_data(
    api_url="https://datahub.creodias.eu/odata/v1",
    query_filter=None
):
    """
    Searches for data in ESA Copernicus Data Space Ecosystem based on a given query filter

    Arguments:
        api_url: API URL
        query_filter: Query string to be passed to the API URL

    Returns:
        Array: List of scenes
    """

    query_url = False
    if query_filter:
        query_url = api_url + query_filter

    scenes = []
    while query_url:
        print(query_url)
        try:
            res = requests.get(query_url)
            if res.status_code == 200:
                data = res.json()
                print("Found %s scenes" % len(data['value']))
                for feature in data['value']:
                    scene = dict(
                        uid=feature['Id'], 
                        scene_id=feature['Name'], 
                        S3Path=feature['S3Path'], 
                        GeoFootprint=feature['GeoFootprint'], 
                        ContentLength=feature['ContentLength'],
                        PublicationDate=feature['PublicationDate'],
                        ModificationDate=feature['ModificationDate']
                    )
                    if 'Attributes' in feature:
                        for attr in feature['Attributes']:
                            scene[attr['Name']] = attr['Value']
                    scenes.append(scene)
            else:
                print("ERROR", res.status_code, res.content)
            if '@odata.nextLink' in data:
                query_url = data['@odata.nextLink']
            else:
                query_url = False 
        except Exception as e: 
            print("ERROR", str(e))

    return scenes


def search_scenes_ingestion(date_from, date_to, filters=None):
    query_template = "/Products?$filter=%filter&$top=1000"
    filter_base = "((PublicationDate ge %date_from and PublicationDate lt %date_to) and (Online eq true))".replace('%date_from', date_from).replace('%date_to', date_to)

    if filters == None:
        filters = [
            "(startswith(Name,'S1') and (contains(Name,'SLC') or contains(Name,'GRD')) and not contains(Name,'_COG') and not contains(Name, 'CARD_BS'))&$expand=Attributes",
            "(startswith(Name,'S2') and (contains(Name,'L2A')) and not contains(Name,'_N9999'))",
            #"(startswith(Name,'S2') and (contains(Name,'L1C') or contains(Name,'L2A')) and not contains(Name,'_N9999'))",
            #"(startswith(Name,'S3A') or startswith(Name,'S3B'))",
            #"(startswith(Name,'S5P') and not contains(Name,'NRTI_'))"
        ]

    scenes = []
    for filter in filters:
        filter_all = filter_base + ' and ' + filter
        query_url = query_template.replace('%filter', filter_all)
        try:
            scenes_current = search_data(query_filter=query_url)
            print("%s scenes found" % len(scenes_current))
            scenes.extend(scenes_current)
        except Exception as e: 
            print("Search failed %s" % (str(e)))

    return scenes




def to_inventory(scene, collection=None, order_id=None, order_status="orderable"):
    uid = scene['uid']
    scene_id = os.path.splitext(scene['scene_id'])[0]
    info = get_scene_id_info(scene_id)
    item_id = scene_id
    id_parts = item_id.split('_')

    tile_id = id_parts[5][1:]
    datetime = parse(info['start'])
    publication_date = parse(scene['PublicationDate']).isoformat()
    modification_date = parse(scene['ModificationDate']).isoformat()
    
    item_geometry = None
    item_bbox = None
    if scene['GeoFootprint']:
        item_geometry = scene['GeoFootprint']
        try:
            item_bbox = geom_fct.calculate_bbox(item_geometry)
        except Exceptuion as e: 
            print(str(e))

    item = pystac.Item(
        id=scene_id,
        datetime=datetime,
        geometry=item_geometry,
        bbox=item_bbox,
        properties={},
    )

    item.properties['esa:uuid'] = uid
    item.properties['esa:scene_id'] = item_id
    if item_id.startswith('S2'):
        item.properties['s2:tile'] = tile_id
        item.properties['s2:baseline'] = id_parts[3]
    
    item.properties['cdse:publication_date'] = publication_date
    item.properties['cdse:modification_date'] = modification_date
    item.properties['version'] = modification_date
    item.properties['deprecated'] = False

    if order_id is not None:
        item.properties['order:id'] = order_id
    if order_status is not None:
        item.properties['order:status'] = order_status
    
    item.properties['terrabyte:folder'] = os.path.join(get_scene_id_folder(item_id), scene['scene_id'])
    if collection:
        item.properties['terrabyte:collection_id'] = collection
    else:
        item.properties['terrabyte:collection_id'] = get_collection_name(item_id)
    item.collection_id = item.properties['terrabyte:collection_id']

    if item_id.startswith('S1'):
        tby_parts = item_id.split('_')
        item.properties['terrabyte:uniq_id'] = '_'.join(tby_parts[0:-1])
    elif item_id.startswith('S2'):
        tby_parts = item_id.split('_')
        tby_parts.pop(3)
        item.properties['terrabyte:uniq_id'] = '_'.join(tby_parts)
    elif item_id.startswith('S3'):
        item.properties['terrabyte:uniq_id'] = f"{info['sensor']}_{info['instrument']}_{info['processingLevel']}_{info['product']}_{info['start']}_{info['stop']}_{info['instance']}"
    elif item_id.startswith('S5'):
        item.properties['terrabyte:collection_id'] = ''
        if '_AUX_' not in item_id:
            item.properties['terrabyte:uniq_id'] = f"{info['sensor']}_{info['category']}_{info['product']}_{info['start']}_{info['stop']}_{info['orbitNumber']}"
        else:
            item.properties['terrabyte:uniq_id'] = item_id

    item.properties['cdse:s3path'] = scene['S3Path']

    item.properties['terrabyte:order'] = dict(
        cdse_id=uid,
        scene_id=item.properties['esa:scene_id'], 
        uniq_id=item.properties['terrabyte:uniq_id'],
        inventory=item.collection_id, 
        collection=item.properties['terrabyte:collection_id'],
        download_folder=get_scene_id_folder(item_id),
        s3path=item.properties['cdse:s3path']
    )

    return item
