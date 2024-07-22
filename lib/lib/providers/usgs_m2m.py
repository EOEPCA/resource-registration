import os
import time
import json
import requests
import pystac
import glob
from pystac_client import Client

from ..base.file import check_file_size
from ..datasets.landsat import get_scene_id_info, get_scene_id_folder


authentication_errors = ["AUTH_INVALID", "AUTH_KEY_INVALID"]
rate_limits = ["RATE_LIMIT", "RATE_LIMIT_USER_DL"]

def sendJSONRequest(url, data, apiKey=None):
    json_data = json.dumps(data)

    headers = {}
    if apiKey is not None:
        headers["X-Auth-Token"] = apiKey

    try:
        response = requests.post(url, json_data, headers=headers)
        if response is None:
            print("No output from service - try again")
            response = requests.post(url, json_data, headers=headers)
            if response is None:
                raise Exception("Could not conduct request twice. URL: %s.")
                return False
    except Exception as e:
        print("Undefined exception: %s" % e)
        return False

    output = json.loads(response.text)
    if output["errorCode"] is not None:
        print(output["errorCode"], "- ", output["errorMessage"])
        if output["errorCode"] in ["RATE_LIMIT", "RATE_LIMIT_USER"]:
            print("Try again because reuqest limit")
            response = requests.post(url, json_data, headers=headers)
            output = json.loads(response.text)
            if output["errorCode"] is not None:
                print(output["errorCode"], "- ", output["errorMessage"])
                raise Exception(
                    "The following error occurred (%s): %s"
                    % (output["errorCode"], output["errorMessage"])
                )
    if response.status_code == 404:
        print("404 Not Found")
        raise Exception(
            "The following error 404 occurred (%s): %s"
            % (output["errorCode"], output["errorMessage"])
        )
    elif response.status_code == 401:
        print("401 Unauthorized")
        raise Exception(
            "The following error 401 occurred (%s): %s"
            % (output["errorCode"], output["errorMessage"])
        )
    elif response.status_code == 400:
        print("Error Code", response.status_code)
        raise Exception(
            "The following error 400 occurred (%s): %s"
            % (output["errorCode"], output["errorMessage"])
        )

    return output["data"]


def login(
    username: str, password: str, token=False, api_url="https://m2m.cr.usgs.gov/api/api/json/stable/"
):
    if token:
        endpoint = "login-token"
        payload = {"username": username, "token": password}
        print("Use login with token")
    else:
        endpoint = "login"
        payload = {"username": username, "password": password}
        print("Use login with password")

    while True:
        api_key = sendJSONRequest(api_url + endpoint, payload)
        if not api_key:
            print("API request failed. Try again...\n")
        else:
            return api_key


def search_data(
    query: dict,
    api_key: str,
    api_url="https://m2m.cr.usgs.gov/api/api/json/stable/",
    download_options=True
):
    scenes = sendJSONRequest(api_url + "scene-search", query, api_key)
    if scenes["recordsReturned"] > 0:
        print(str(scenes["recordsReturned"]) + " scenes found.\n")

        if download_options:

            sceneIds = []
            for result in scenes["results"]:
                # Add this scene to the list to download
                sceneIds.append(result["entityId"])

            return get_download_options(query["datasetName"], sceneIds)

        else:
            return scenes
    else:
        print("Search returned no results. Check query!\n")
        return []


def get_download_options(datasetName, sceneIds, api_key, api_url = "https://m2m.cr.usgs.gov/api/api/json/stable/"):
    # Find the download options for these scenes
    # NOTE :: Remember the scene list cannot exceed 50,000 items!
    payload = {"datasetName": datasetName, "entityIds": sceneIds}

    downloadOptions = sendJSONRequest(
        api_url + "download-options", payload, api_key
    )

    if downloadOptions is None:
        print("No downloadable scenes found.\n")
        return []
    else:
        # Aggregate a list of available products
        downloads = []
        #downloads_systems = dict()
        downloads_uniq = []
        for product in downloadOptions:
            # Make sure the product is available for this scene
            if product["available"] is True and product["downloadSystem"] != "folder":
                # We should only return a scene once (not duplicates from additional download systems)
                # -> TODO: this is currently a LANDSAT specific use case - not valid for MODIS!
                #if product["downloadSystem"] not in downloads_systems:
                #    downloads_systems[product["downloadSystem"]] = []

                if product["entityId"] not in downloads_uniq:
                    item = {
                        "entityId": product["entityId"],
                        "displayId": product["displayId"],
                        "productId": product["id"],
                        "download_system": product["downloadSystem"],
                    }
                    downloads.append(item)
                    #downloads_systems[product["downloadSystem"]].append(item)
                    downloads_uniq.append(product["entityId"])

        print(str(len(downloads)) + " downloadable data records found.")
        return downloads
    
def get_download_urls(
    downloads: list,
    api_key,
    label = "",
    api_url = "https://m2m.cr.usgs.gov/api/api/json/stable/",
):
    if label == "":
        label = str(int(time.time() * 1000))
       
    print("Label: %s" % label)

    payload = {"downloads": downloads, "label": label} # , "returnAvailable": True, "configurationCode": "order"

    # Call the download to get the direct download url
    results = sendJSONRequest(api_url + "download-request", payload, api_key)
    #print(str(results))
    while not results:
        print("API request failed. Try again...\n")
        results = sendJSONRequest(api_url + "download-request", payload, api_key)
    
    #with open('%s_download_reqest.json' % label, 'w') as f:
    #    x = f.write(json.dumps(results, indent=4))
    
    print('available: %s' % len(results["availableDownloads"]))
    print('preparing: %s' % len(results["preparingDownloads"]))
    print('duplicates: %s' % len(results["duplicateProducts"]))
    print('failed: %s' % len(results["failed"]))
    print('newRecords: %s' % len(results["newRecords"]))
    print('numInvalidScenes: %s' % results['numInvalidScenes'])
    
    download_urls = []
    if len(results["availableDownloads"]) > 0:
         for result in results["availableDownloads"]:
            print(f"Get download url: {result['url']}\n")
            download_urls.append(result)

    payload = {"label": label}
    results = sendJSONRequest(api_url + "download-retrieve", payload, api_key)
    while not results:
        print("API request failed. Try again...\n")
        results = sendJSONRequest(api_url + "download-retrieve", payload, api_key)

    queued = False
    while results['queueSize'] > 0:
        queued = True
        print("Queue Size: %s - try again in 15 seconds" % results['queueSize'])
        time.sleep(15)
        results = sendJSONRequest(api_url + "download-retrieve", payload, api_key)
        while not results:
            print("API request failed. Try again...\n")
            results = sendJSONRequest(api_url + "download-retrieve", payload, api_key)

    if results is not False:
        for result in results["available"]:
            print(f"Get download url: {result['url']}\n")
            download_urls.append(result)

        for result in results["requested"]:
            print(f"Get download url: {result['url']}\n")
            download_urls.append(result)

    return download_urls


def add_download_urls(scenes, api_key):
    search_query = dict()
    scenes_all = dict()
    for scene in scenes:
        scenes_all[scene['scene_id']] = scene
        datasetName = scene['inventory'].replace('-','_')
        if datasetName not in search_query:
            search_query[datasetName] = []
        search_query[datasetName].append(scene["landsat_id"])

    results_all = []
    for datasetName in search_query:
        print("Found %s scenes for %s collection" % (len(search_query[datasetName]), datasetName))
        if len(search_query[datasetName]) > 0:
            results = get_download_options(datasetName, search_query[datasetName], api_key=api_key)
            print("Find %s results for %s" % (len(results), datasetName))
            results_all.extend(results)

    print("Found %s results" % len(results_all))
    if len(results_all) == 0:
        raise Exception("No scenes found")

    downloads = get_download_urls(downloads=results_all, api_key=api_key)
    print("Found %s downloads" % len(downloads))

    scenes = []
    scenes_added = []
    for item in downloads:
        url = item['url']
        if 'displayId' in item:
            id = item['displayId']
        elif url.startswith('https://landsatlook.usgs.gov'):
            id = url.replace('https://landsatlook.usgs.gov/gen-bundle?landsat_product_id=', '').split('&')[0]
        else:
            id = None

        if id in scenes_all:
            scenes_all[id]['url'] = url
            if id not in scenes_added:
                scenes.append(scenes_all[id])
                scenes_added.append(id)
        else:
            scenes.append(dict(url=url))

    return scenes

def download_data(
    url,
    output_dir,
    chunk_size=1024 * 1000,
    timeout=300
):
    """
    Download single file from USGS M2M by download url
    """

    try:
        print("Waiting for server response...")
        r = requests.get(url, stream=True, allow_redirects=True, timeout=timeout)
        expected_file_size = int(r.headers.get("content-length", 0))
        file_name = r.headers["Content-Disposition"].split('"')[1]
        print(f"Filename: {file_name}")
        file_path = os.path.join(output_dir, file_name)
        # TODO: Check for existing files and whether they have the correct file size
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(file_path, "wb") as f:
            start = time.perf_counter()
            print(f"Download of {file_name} in progress...")
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
            duration = time.perf_counter() - start
            speed = round((expected_file_size / duration) / (1000 * 1000), 2)

        if check_file_size(expected_file_size, file_path):
            print(
                f"Download of {file_name} successful. Average download speed: {speed} MB/s"
            )
            return file_path
        else:
            os.remove(file_path)
            print(f"Failed to download from {url}")
            return False
    except Exception as e:
        print(e)
        print(f"Failed to download from {url}.")
        return False


def download_aria(scene, basedir, aria2):
    if 'scene_id' in scene:
        scene_id = scene['scene_id']
        path = get_scene_id_folder(scene['scene_id'])
        directory = os.path.join(basedir, path)
        filename = scene['scene_id'] + '.tar'
        download = aria2.add_uris([scene['url']], {"dir": directory, "out": filename, "continue": "true", "allow-overwrite": "true"})

        return {
            "gid": download.gid, 
            "file_path": os.path.join(directory, filename)
        }
    else:
        # In this case we do not have a filename before downloading
        directory = os.path.join(basedir, '.download')
        download = aria2.add_uris([scene['url']], {"dir": directory, "continue": "true", "allow-overwrite": "true"})
        return {
            "gid": download.gid
        }


def search_data_stac(collections, query, max_items=10000, api_url="https://landsatlook.usgs.gov/stac-server"):
    params = {
        "max_items": max_items,
        "collections": collections,
        "query": query 
    }

    items=[]
    try:
        cat = Client.open(api_url)
        search = cat.search(**params)
        items = list(search.items_as_dicts())
        for i in items:
            del i['assets']
            i['id'] = i['id'].replace('_SR', '')
        print("%s scenes found" % len(items))
    except Exception as e:
        print("FAILED", str(e))
    return items


def search_data_ingestion(date_from, date_to, collections="landsat-c2l2-sr"):
    query = {
        "created": {
            "gte": date_from,
            "lt": date_to
        }
    }
    return search_data_stac(collections=collections, query=query)


collections = {
    "LC_C2_L1": "landsat-ot-c2-l1",
    "LC_C2_L2": "landsat-ot-c2-l2",
    "LE_C2_L1": "landsat-etm-c2-l1",
    "LE_C2_L2": "landsat-etm-c2-l2",
    "LT_C2_L1": "landsat-tm-c2-l1",
    "LT_C2_L2": "landsat-tm-c2-l2"
}


def get_collection_name(scene_id):
    parts = scene_id.split('_')
    sensor = parts[0][0:2]
    collection = "C" + parts[5][1]
    level = parts[1][0:2]
    name = f"{sensor}_{collection}_{level}"
    if name in collections: 
        return collections[name]
    else:
        raise Exception(f"Could not find {name} in pre-defined collections for scene {scene_id}")


def to_inventory_from_stac(item, order_status="orderable", order_id=None, batch_id=None):
    if 'collection' in item:
        del item['collection']

    if 'links' in item: 
        del item['links']

    
    item = pystac.Item.from_dict(item)
    item_id = item.id
    item_parts = item_id.split('_')
    item_parts.pop(4)
    tby_item_id = '_'.join(item_parts)

    item.properties['deprecated'] = False
    if order_status is not None:
        item.properties['order:status'] = order_status
    if order_id:
        item.properties['order:id'] = order_id
    if batch_id:
        item.properties['order:batch_id'] = batch_id
    item.properties['version'] = item.properties['updated']

    item.properties['landsat:scene_id'] = item.properties['landsat:scene_id']
    item.properties['landsat:wrs_row'] = int(item.properties['landsat:wrs_row'])
    item.properties['landsat:wrs_path'] = int(item.properties['landsat:wrs_path'])

    item.properties['terrabyte:item_id'] = tby_item_id
    item.properties['terrabyte:folder'] = os.path.join(get_scene_id_folder(item_id), item_id)
    item.properties['terrabyte:collection_id'] = get_collection_name(item_id)

    item.properties['terrabyte:order'] = dict(
        scene_id=item.id,
        landsat_id=item.properties['landsat:scene_id'],
        inventory=item.properties['terrabyte:collection_id'], 
        collection=item.properties['terrabyte:collection_id'],
        download_folder=get_scene_id_folder(item_id)
    )

    item.collection_id = item.properties['terrabyte:collection_id']

    return item
