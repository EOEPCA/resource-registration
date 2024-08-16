import os
import re
import json
import glob
import copy
import logging
import pystac
import requests
from datetime import datetime

from ..resources.stac import (
    extract_stactools,
    add_asset_filesize,
)

# https://www.usgs.gov/faqs/what-naming-convention-landsat-collections-level-1-scenes
scene_id_pattern = (
    r"^L"
    r"(?P<sensor>C|O|T|E|T|M)"
    r"(?P<satellite>[0-9]{2})_"
    r"(?P<processingLevel>[0-9A-Z]{4})_"
    r"(?P<wrsPath>[0-9]{3})"
    r"(?P<wrsRow>[0-9]{3})_"
    r"(?P<start>[0-9]{8})_"
    r"(?P<processingTime>[0-9]{8})_"
    r"(?P<collectionNumber>[0-9]{2})_"
    r"(?P<collectionCategory>[A-Z0-9]{2})$"
)

sensor_name = {
    "C": "oli-tirs",
    "O": "oli",
    # "T": "tirs",
    "E": "etm",
    "T": "tm",
    "M": "mss",
}

asset_changes = {
    "LT": {  # for Landsat 4 and 5
        "blue": ["B01", "Blue Band (B01)"],
        "green": ["B02", "Green Band (B02)"],
        "red": ["B03", "Red Band (B03)"],
        "nir08": ["B04", "Near Infrared Band 0.8 (B04)"],
        "swir16": ["B05", "Short-wave Infrared Band 1.6 (B05)"],
        "lwir": ["B06", "Surface Temperature Band (B06)"],
        "swir22": ["B07", "Short-wave Infrared Band 2.2 (B07)"],
        "atmos_opacity": ["Atmos_Opacity", ""],
        "atran": ["ATRAN", ""],
        "cdist": ["CDIST", ""],
        "drad": ["DRAD", ""],
        "urad": ["URAD", ""],
        "trad": ["TRAD", ""],
        "emis": ["EMIS", ""],
        "emsd": ["EMSD", ""],
        "qa_pixel": ["QA_Pixel", ""],
        "qa_radsat": ["QA_Radsat", ""],
        "qa": ["QA_Temp", ""],
        "cloud_qa": ["QA_Cloud", ""],
    },
    "LE": {  # for Landsat 7
        "blue": ["B01", "Blue Band (B01)"],
        "green": ["B02", "Green Band (B02)"],
        "red": ["B03", "Red Band (B03)"],
        "nir08": ["B04", "Near Infrared Band 0.8 (B04)"],
        "swir16": ["B05", "Short-wave Infrared Band 1.6 (B05)"],
        "lwir": ["B06", "Surface Temperature Band (B06)"],
        "swir22": ["B07", "Short-wave Infrared Band 2.2 (B07)"],
        "atmos_opacity": ["Atmos_Opacity", ""],
        "atran": ["ATRAN", ""],
        "cdist": ["CDIST", ""],
        "drad": ["DRAD", ""],
        "urad": ["URAD", ""],
        "trad": ["TRAD", ""],
        "emis": ["EMIS", ""],
        "emsd": ["EMSD", ""],
        "qa_pixel": ["QA_Pixel", ""],
        "qa_radsat": ["QA_Radsat", ""],
        "qa": ["QA_Temp", ""],
        "cloud_qa": ["QA_Cloud", ""],
    },
    "LC": {  # for Landsat 8 and 9
        "coastal": ["B01", "Coastal/Aerosol Band (B01)"],
        "blue": ["B02", "Blue Band (B02)"],
        "green": ["B03", "Green Band (B03)"],
        "red": ["B04", "Red Band (B04)"],
        "nir08": ["B05", "Near Infrared Band 0.8 (B05)"],
        "swir16": ["B06", "Short-wave Infrared Band 1.6 (B06)"],
        "lwir11": ["B10", "Surface Temperature Band (B10)"],
        "swir22": ["B07", "Short-wave Infrared Band 2.2 (B07)"],
        "atran": ["ATRAN", ""],
        "cdist": ["CDIST", ""],
        "drad": ["DRAD", ""],
        "urad": ["URAD", ""],
        "trad": ["TRAD", ""],
        "emis": ["EMIS", ""],
        "emsd": ["EMSD", ""],
        "qa_pixel": ["QA_Pixel", ""],
        "qa_radsat": ["QA_Radsat", ""],
        "qa": ["QA_Temp", ""],
        "qa_aerosol": ["QA_Aerosol", ""],
    },
}

folder_structure = "level-{processingLevelNo}/standard/{sensor}/{year}/{wrsPath}/{wrsRow}"


def get_scene_id_info(scene_id):
    """
    Description...

    Parameters:
        scene_id: x


    Returns:
        (...): ...
    """
    match = re.match(re.compile(scene_id_pattern), scene_id)
    return match.groupdict()


def get_scene_id_folder(scene_id, folder_format=None):
    """
    Description...

    Parameters:
        scene_id: x
        folder_format: x

    Returns:
        (...): ...
    """
    variables = get_scene_id_info(scene_id)
    if "start" in variables:
        date = datetime.strptime(variables["start"], "%Y%m%d")
        variables["year"] = date.strftime("%Y")
        variables["month"] = date.strftime("%m")
        variables["day"] = date.strftime("%d")
    if "sensor" in variables:
        variables["sensor"] = sensor_name[variables["sensor"]]
    if "processingLevel" in variables:
        variables["processingLevelNo"] = variables["processingLevel"][1]

    if folder_format is None:
        folder_format = folder_structure

    return folder_format.format(**variables)


def landsat_metadata(scene_path, scene_id, return_pystac=False, add_file_size=False):
    """
    Description...

    Parameters:
        scene_path: x
        scene_id: x
        return_pystac: x
        add_file_size: x

    Returns:
        (...): ...

    Raises:
        Exception: Metadata_error: Folder does not exist.
        Exception: Metadata_error: No *_MTL.xml file available in folder.
        Exception: Metadata_error: Error during creating metadata.
    """
    if scene_path[-1] == "/":
        scene_path = scene_path[:-1]
    print("executing landsat_metadata for %s" % scene_path)
    if not os.path.exists(scene_path):
        raise Exception("metadata_error: Folder does not exist %s" % (scene_path))
    stac_function = "stactools.landsat.stac.create_item"
    stac_function_options = {"use_usgs_geometry": False}
    landsat_mtl_xml = glob.glob(os.path.join(scene_path, "*_MTL.xml"))
    if len(landsat_mtl_xml) == 0:
        metadata_error = "No *_MTL.xml file available in folder %s" % (scene_path,)
        raise Exception("metadata_error: %s" % metadata_error)
    landsat_mtl_xml = landsat_mtl_xml[0]
    print("MTL file: %s" % landsat_mtl_xml)

    try:
        stac_file = os.path.join(scene_path, scene_id + ".STAC.json")
        stac_item = extract_stactools(landsat_mtl_xml, stac_function, stac_function_options)
        stac_item.id = scene_id
        stac_item = modify_landsat_stac(stac_item)
        if add_file_size:
            stac_item = add_asset_filesize(stac_item)
        if return_pystac:
            return stac_item
        else:
            with open(stac_file, "w") as f:
                f.write(json.dumps(stac_item.to_dict()))
            return stac_file

    except Exception as e:
        metadata_error = "Error during creating metadata for %s: %s" % (
            scene_path,
            str(e),
        )
        raise Exception("metadata_error: %s" % metadata_error)


def adapt_stac_metadata(scene_path):
    """
    Changes hrefs in existing Landsat STAC-Metadata

    Parameters:
        scene_path: x

    Returns:
        (...): ...

    Raises:
        Exception: Failed to adapt STAC-metadata.
    """

    print(f"Adapt STAC-metadata of {scene_path}.")
    # for all STAC-metadata files do
    stac_jsons = []
    for file in os.listdir(scene_path):
        if file.endswith("stac.json"):
            stac_jsons.append(file)

    stac_files = []
    if len(stac_jsons) > 0:
        try:
            for file in stac_jsons:
                # read in stac.json
                with open(os.path.join(scene_path, file), "r") as stac_file:
                    data = json.load(stac_file)
                    if "created" not in data["properties"]:
                        data["properties"]["created"] = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))

                    # adapt all assets
                    for asset in data["assets"]:
                        href_old = data["assets"][asset]["href"]
                        file_name = os.path.basename(href_old)
                        # href_new = os.path.join(scene_path,file_name) # keep relative paths
                        href_new = file_name
                        data["assets"][asset]["href"] = href_new
                        if "alternate" in data["assets"][asset]:
                            del data["assets"][asset]["alternate"]

                    # remove index asset
                    if "index" in data["assets"]:
                        del data["assets"]["index"]

                    # remove all links
                    data["links"] = []

                # write .COG .json file
                with open(os.path.join(scene_path, file), "w") as jsonFile:
                    json.dump(data, jsonFile, indent=4)
                stac_files.append(os.path.join(scene_path, file))
            print(f"STAC-metadata of {scene_path} successfully adapted")

        except Exception as e:
            print(e)
            print(f"Failed to adapt STAC-metadata of {scene_path}")
    else:
        print(f"{scene_path} does not contain STAC-metadata to adapt.")

    return stac_files


__log = logging.getLogger("Log Info")


def modify_landsat_stac(stac_item: pystac.item.Item):
    """
    Modify the Asset-Keys and eo:bands:name for a Landsat L2 STAC-Item.

    Args:
        stac_item: The STAC item file to modify. Must be a STACObject.

    Returns:
        (...): A pystac.item.Item object with the desired changes.

    Raises:
        Exception: Could not find entry in asset_changes configuration.
    """

    stac_item_dict = copy.deepcopy(stac_item.to_dict(include_self_link=False))

    if stac_item_dict["geometry"]["type"] == "MultiPolygon":
        try:
            link = stac_item_dict["links"][1]["href"]
            stac_item_usgs = requests.get(link).json()
            stac_item_dict["geometry"] = stac_item_usgs["geometry"]
        except Exception:
            pass

    mission = stac_item.id[0:2]  # Get first two characters of Item id (e.g., LC for LC09_L2SR_....)
    if mission not in asset_changes:
        raise Exception("Could not find entry for %s in asset_changes configuration" % mission)
    input_dict = asset_changes[mission]

    for i, (current_key, target_key) in enumerate(input_dict.items()):
        __log.info(f"Replacing the current Asset-Key {current_key} with the new Asset-Key {target_key[0]}.")
        try:
            stac_item_dict["assets"][target_key[0]] = copy.deepcopy(stac_item_dict["assets"].pop(current_key))
            if "eo:bands" in stac_item_dict["assets"][target_key[0]]:
                stac_item_dict["assets"][target_key[0]]["eo:bands"][0]["name"] = target_key[0]
                stac_item_dict["assets"][target_key[0]]["title"] = target_key[1]
        except Exception:
            __log.info(f"{current_key} is not a Asset in this STAC-Item.")

    if "proj:centroid" in stac_item_dict["properties"]:
        for key in stac_item_dict["properties"]["proj:centroid"]:
            stac_item_dict["properties"]["proj:centroid"][key] = float(
                stac_item_dict["properties"]["proj:centroid"][key]
            )

    stac_item_object_final = pystac.Item.from_dict(stac_item_dict)
    return stac_item_object_final
