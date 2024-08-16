import os
import re
import json
import copy
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
import pystac

from ..base.file import calculate_checksum
from ..resources.stac import (
    extract_stactools,
    add_asset_filesize,
)


# scene_id_patterns = {
#     "S1":
#         r"^(?P<sensor>S1[AB])_"
#         r"(?P<beam>S1|S2|S3|S4|S5|S6|IW|EW|WV|EN|N1|N2|N3|N4|N5|N6|IM)_"
#
#         r"(?P<product>SLC|GRD|OCN)"
#         r"(?P<resolution>F|H|M|_)_"
#         r"(?P<processingLevel>1|2)"
#         r"(?P<category>S|A)"
#         r"(?P<pols>SH|SV|DH|DV|VV|HH|HV|VH)_"
#         r"(?P<start>[0-9]{8}T[0-9]{6})_"
#         r"(?P<stop>[0-9]{8}T[0-9]{6})_"
#         r"(?P<orbitNumber>[0-9]{6})_"
#         r"(?P<dataTakeID>[0-9A-F]{6})_"
#         r"(?P<productIdentifier>[0-9A-F]{4})$",
#     "S2":
#         r"^(?P<sensor>S2[AB])_"
#         r"MSI"
#         r"(?P<level>L1C|L2A)_"
#         r"(?P<start>[0-9]{8}T[0-9]{6})_"
#         r"(?P<processingBaseline>N[0-9]{4})_"
#         r"R(?P<orbitNumber>[0-9]{3})_"
#         r"T(?P<utm_zone>[0-9]{2})"
#         r"(?P<mgrs_lat>[A-Z]{1})"
#         r"(?P<square>[A-Z]{2})_"
#         r"(?P<productDiscriminator>[0-9]{8}T[0-9]{6})$",
#     "S3":
#         r"^(?P<sensor>S3[AB])_"
#         r"(?P<instrument>OL|SL|SR|DO|MW|GN|SY|TM|AX)_"
#         r"(?P<processingLevel>0|1|2)_"
#         r"(?P<product>[A-Z0-9_]{6})_"
#         r"(?P<start>[0-9]{8}T[0-9]{6})_"
#         r"(?P<stop>[0-9]{8}T[0-9]{6})_"
#         r"(?P<productDiscriminator>[0-9]{8}T[0-9]{6})_"
#         r"(?P<instance>[A-Z0-9_]{17})_"
#         r"(?P<center>[A-Z0-9_]{3})_"
#         r"(?P<class>[A-Z0-9_]{8})$",
#     "S5":
#         r"^(?P<sensor>S5P)_"
#         r"(?P<fileclass>[A-Z]{4})_"
#         r"(?P<category>[A-Z0-9_]{3})_"
#         r"(?P<product>[A-Z0-9_]{6})_"
#         r"(?P<start>[0-9]{8}T[0-9]{6})_"
#         r"(?P<stop>[0-9]{8}T[0-9]{6})_"
#         r"(?P<orbitNumber>[0-9]{5})_"
#         r"(?P<collection>[0-9]{2})_"
#         r"(?P<processorVersion>[0-9]{6})_"
#         r"(?P<productionDate>[0-9]{8}T[0-9]{6})$",
#     "S5P_AUX":
#         r"^(?P<sensor>S5P)_"
#         r"(?P<fileclass>[A-Z]{4})_"
#         r"(?P<category>[A-Z0-9_]{3})_"
#         r"(?P<product>[A-Z0-9_]{6})_"
#         r"(?P<start>[0-9]{8}T[0-9]{6})_"
#         r"(?P<stop>[0-9]{8}T[0-9]{6})_"
#         r"(?P<productionDate>[0-9]{8}T[0-9]{6})$"
# }
# Todo: Check Formatter pattern Changes (old commented out)
scene_id_patterns = {
    "S1": r"^(?P<sensor>S1[AB])_"
    r"(?P<beam>S1|S2|S3|S4|S5|S6|IW|EW|WV|EN|N1|N2|N3|N4|N5|N6|IM)_"
    r"(?P<product>SLC|GRD|OCN)"
    r"(?P<resolution>F|H|M|_)_"
    r"(?P<processingLevel>1|2)"
    r"(?P<category>S|A)"
    r"(?P<pols>SH|SV|DH|DV|VV|HH|HV|VH)_"
    r"(?P<start>[0-9]{8}T[0-9]{6})_"
    r"(?P<stop>[0-9]{8}T[0-9]{6})_"
    r"(?P<orbitNumber>[0-9]{6})_"
    r"(?P<dataTakeID>[0-9A-F]{6})_"
    r"(?P<productIdentifier>[0-9A-F]{4})$",
    "S2": r"^(?P<sensor>S2[AB])_"
    r"MSI"
    r"(?P<level>L1C|L2A)_"
    r"(?P<start>[0-9]{8}T[0-9]{6})_"
    r"(?P<processingBaseline>N[0-9]{4})_"
    r"R(?P<orbitNumber>[0-9]{3})_"
    r"T(?P<utm_zone>[0-9]{2})"
    r"(?P<mgrs_lat>[A-Z]{1})"
    r"(?P<square>[A-Z]{2})_"
    r"(?P<productDiscriminator>[0-9]{8}T[0-9]{6})$",
    "S3": r"^(?P<sensor>S3[AB])_"
    r"(?P<instrument>OL|SL|SR|DO|MW|GN|SY|TM|AX)_"
    r"(?P<processingLevel>0|1|2)_"
    r"(?P<product>[A-Z0-9_]{6})_"
    r"(?P<start>[0-9]{8}T[0-9]{6})_"
    r"(?P<stop>[0-9]{8}T[0-9]{6})_"
    r"(?P<productDiscriminator>[0-9]{8}T[0-9]{6})_"
    r"(?P<instance>[A-Z0-9_]{17})_"
    r"(?P<center>[A-Z0-9_]{3})_"
    r"(?P<class>[A-Z0-9_]{8})$",
    "S5": r"^(?P<sensor>S5P)_"
    r"(?P<fileclass>[A-Z]{4})_"
    r"(?P<category>[A-Z0-9_]{3})_"
    r"(?P<product>[A-Z0-9_]{6})_"
    r"(?P<start>[0-9]{8}T[0-9]{6})_"
    r"(?P<stop>[0-9]{8}T[0-9]{6})_"
    r"(?P<orbitNumber>[0-9]{5})_"
    r"(?P<collection>[0-9]{2})_"
    r"(?P<processorVersion>[0-9]{6})_"
    r"(?P<productionDate>[0-9]{8}T[0-9]{6})$",
    "S5P_AUX": r"^(?P<sensor>S5P)_"
    r"(?P<fileclass>[A-Z]{4})_"
    r"(?P<category>[A-Z0-9_]{3})_"
    r"(?P<product>[A-Z0-9_]{6})_"
    r"(?P<start>[0-9]{8}T[0-9]{6})_"
    r"(?P<stop>[0-9]{8}T[0-9]{6})_"
    r"(?P<productionDate>[0-9]{8}T[0-9]{6})$",
}

folder_structures = {
    "S1": "{product}/{year}/{month}/{day}",
    "S2": "{level}/tiles/{utm_zone}/{mgrs_lat}/{square}/{year}/{month}",
    "S3": "{instrument}/{product}/{year}/{month}/{day}",
    "S5": "{category}/{product}/{year}/{month}/{day}",
}

checksum_settings = {
    "S1": dict(file="manifest.safe", algorithm="MD5"),
    "S2": dict(file="manifest.safe", algorithm="SHA3-256"),
    "S3": dict(file="xfdumanifest.xml", algorithm="MD5"),
}

asset_changes = {
    "S2": {
        "coastal": "B01",
        "blue": "B02",
        "green": "B03",
        "red": "B04",
        "rededge1": "B05",
        "rededge2": "B06",
        "rededge3": "B07",
        "nir": "B08",
        "nir08": "B8A",
        "nir09": "B09",
        "cirrus": "B10",
        "swir16": "B11",
        "swir22": "B12",
        "visual": "TCI",
        "aot_10m": "AOT",
        "wvp_10m": "WVP",
        "scl": "SCL",
    }
}

variable_mappings = {"S3": {"OL": "OLCI", "SL": "SLSTR", "SY": "SYNERGY"}}


def get_scene_id_info(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...

    Raises:
        Exception: Satellite not supported.
    """
    satellite = scene_id[0:2]
    if satellite == "S5" and "_AUX_" in scene_id:
        satellite = "S5P_AUX"
    if satellite not in scene_id_patterns:
        raise Exception("Satellite %s not supported" % satellite)

    match = re.match(re.compile(scene_id_patterns[satellite]), scene_id)
    variables = match.groupdict()
    if "category" in variables:
        variables["category"] = variables["category"].rstrip("_")
    if "product" in variables:
        variables["product"] = variables["product"].rstrip("_").replace("___", "_").replace("__", "_")
    return variables


def get_scene_id_folder(scene_id, folder_format=None):
    """
    Description...

    Parameters:
        scene_id: x
        folder_format: x

    Returns:
        (...): ...

    Raises:
        Exception: Satellite not supported.
        Exception: Not supported for integrity check.
        Exception: manifest.safe not found.
        Exception: File does not match expected file size.
        Exception: File does not match expected checksum.
    """
    variables = get_scene_id_info(scene_id)
    if "start" in variables:
        date = datetime.strptime(variables["start"], "%Y%m%dT%H%M%S")
        variables["year"] = date.strftime("%Y")
        variables["month"] = date.strftime("%m")
        variables["day"] = date.strftime("%d")

    if scene_id.startswith("S3"):
        if "instrument" in variables:
            variables["instrument"] = variable_mappings["S3"][variables["instrument"]]
        if "product" in variables:
            variables["product"] = (
                variables["instrument"][0:2] + "_" + variables["processingLevel"] + "_" + variables["product"] + "___"
            )

    if folder_format is None:
        satellite = scene_id[0:2]
        if satellite not in folder_structures:
            raise Exception("Satellite %s not supported" % satellite)
        folder_format = folder_structures[satellite]

    return folder_format.format(**variables)


def validate_integrity(scene_path, scene_id):
    """
    Description...

    Parameters:
        scene_path: x
        scene_id: x

    Returns:
        (...): ...

    Raises:
        Exception: Not supported for integrity check.
        Exception: manifest.safe not found.
        Exception: File does not match expected file size.
        Exception: File does not match expected checksum.
    """
    if scene_id[0:2] not in checksum_settings:
        raise Exception("%s not supported for integrity check (%s)" % (scene_id[0:2], scene_id))
    settings = checksum_settings[scene_id[0:2]]
    checksum_alg = settings["algorithm"]
    index_file_name = settings["file"]

    manifest = os.path.join(scene_path, index_file_name)
    if not os.path.exists(manifest):
        raise Exception("manifest.safe not found: %s" % manifest)

    tree = ET.parse(manifest)
    root = tree.getroot()
    for f in root.findall(".//byteStream"):
        href = f.find("fileLocation").attrib["href"]
        check_file = os.path.join(scene_path, href)
        size = os.stat(check_file).st_size
        expected_file_size = int(f.attrib["size"])
        if size != expected_file_size:
            raise Exception(
                "File %s does not match expected file size: %s vs. %s" % (check_file, size, expected_file_size)
            )

        expected_checksum = f.find("checksum").text.lower()
        # checksum_alg = "SHA3-256"
        checksum = calculate_checksum(checksum_alg, check_file)
        if checksum != expected_checksum:
            raise Exception(
                "File %s does not match expected checksum (%s): %s vs. %s"
                % (check_file, checksum_alg, size, expected_checksum)
            )

    return True


def sentinel_metadata(scene_path, scene_id, return_pystac=False, add_file_size=False):
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
        Exception: Metadata_error: No STAC function for this scene.
        Exception: Error during creating metadata.
    """
    if scene_path[-1] == "/":
        scene_path = scene_path[:-1]
    print("executing sentinel_metadata for %s" % scene_path)

    if not os.path.exists(scene_path):
        raise Exception("metadata_error: Folder does not exist %s" % (scene_path))

    stac_function = None
    stac_function_args = {}
    if scene_id.startswith("S1") and "_GRD" in scene_id:
        stac_function = "stactools.sentinel1.stac.create_item"
    elif scene_id.startswith("S1") and "_SLC" in scene_id:
        stac_function = "stactools.sentinel1.stac.create_item"
    elif scene_id.startswith("S2"):
        stac_function = "stactools.sentinel2.stac.create_item"
    elif scene_id.startswith("S3"):
        stac_function = "stactools.sentinel3.stac.create_item"
        stac_function_args = dict(skip_nc=True)
    else:
        raise Exception("metadata_error: No STAC function for %s" % scene_id)

    base_item = None
    collection = get_collection_name(scene_id)
    if collection == "sentinel-2-c1-l2a":
        base_item = os.path.join(os.path.dirname(__file__), "collections", "sentinel", "sentinel-2-c1-l2a.json")
    elif collection == "sentinel-2-c1-l1c":
        base_item = os.path.join(os.path.dirname(__file__), "collections", "sentinel", "sentinel-2-c1-l1c.json")
    elif collection == "sentinel-3-olci-l1-efr":
        base_item = os.path.join(os.path.dirname(__file__), "collections", "sentinel", "sentinel-3-olci-l1-efr.json")

    try:
        stac_file = os.path.join(scene_path, scene_id + ".STAC.json")
        stac_item = extract_stactools(scene_path, stac_function, stac_function_args)
        stac_item.properties["terrabyte:stactools_id"] = stac_item.id
        stac_item.id = scene_id

        if base_item:
            base_item = json.load(open(base_item))
            if "item_assets" in base_item:
                base_item["assets"] = base_item["item_assets"]

        if scene_id.startswith("S2"):
            stac_item = modify_s2_stac(stac_item, base_item=base_item)
        elif scene_id.startswith("S3"):
            stac_item = modify_s3_stac(stac_item, base_item=base_item)

        # Add file:// protocol for local file paths
        for asset in stac_item.assets:
            if stac_item.assets[asset].href.startswith("/"):
                stac_item.assets[asset].href = "file://%s" % stac_item.assets[asset].href

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


def get_collection_name(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...

    Raises:
        Exception: No collection found.
    """
    if scene_id.startswith("S1") and "_GRD" in scene_id:
        return "sentinel-1-grd"
    elif scene_id.startswith("S1") and "_SLC" in scene_id:
        return "sentinel-1-slc"
    elif scene_id.startswith("S2") and "_MSIL1C_" in scene_id:
        return "sentinel-2-c1-l1c"
    elif scene_id.startswith("S2") and "_MSIL2A_" in scene_id:
        return "sentinel-2-c1-l2a"
    elif scene_id.startswith("S3") and "_OL_1_EFR_" in scene_id:
        return "sentinel-3-olci-l1-efr"
    elif scene_id.startswith("S5") and "_L1B_" in scene_id:
        return "sentinel-5p-l1b"
    elif scene_id.startswith("S5") and "_L2_" in scene_id:
        return "sentinel-5p-l2"
    elif scene_id.startswith("S5") and "_AUX_" in scene_id:
        return "sentinel-5p-aux"
    else:
        raise Exception("No collection found")


__log = logging.getLogger("Log Info")


def modify_s2_stac(stac_item: pystac.item.Item, base_item=None):
    """
    Modify the Asset-Keys and eo:bands:name for a Sentinel-2 L2 STAC-Item.

    Args:
        stac_item: The STAC item file/object to modify. Must be a STACObject.
        base_item: x

    Returns:
        (...): A pystac.item.Item object with the desired changes.

    Raises:
        Exception: Could not find entry in asset_changes configuration.
    """

    stac_item_dict = copy.deepcopy(stac_item.to_dict(include_self_link=False))

    mission = stac_item.id[0:2]  # Get first two characters of Item id (e.g., S2 for S2A_MSIL2A_....)
    if mission not in asset_changes:
        raise Exception("Could not find entry for %s in asset_changes configuration" % mission)
    input_dict = asset_changes[mission]
    assets_new = dict()

    for i, (current_key, target_key) in enumerate(input_dict.items()):

        if current_key in stac_item_dict["assets"]:
            __log.info(f"Replacing the current Asset-Key {current_key} with the new Asset-Key {target_key}.")
            assets_new[target_key] = copy.deepcopy(stac_item_dict["assets"].pop(current_key))
        else:
            __log.info(
                (
                    f"Replacing the current Asset-Key {current_key} with the new Asset-Key {target_key}: "
                    f"Current key not found in metadata!"
                )
            )

    if base_item:
        try:
            for key in base_item["assets"]:
                if key not in assets_new:
                    assets_new[key] = copy.deepcopy(stac_item_dict["assets"][key])
                for property in base_item["assets"][key]:
                    assets_new[key][property] = copy.deepcopy(base_item["assets"][key][property])

        except Exception as e:
            __log.error("ERROR: %s" % e)

    stac_item_dict["assets"] = assets_new
    stac_item_object_final = pystac.Item.from_dict(stac_item_dict)
    return stac_item_object_final


def modify_s3_stac(stac_item: pystac.item.Item, base_item=None):
    """
    Modify the Asset-Keys and eo:bands:name for a Sentinel-3 STAC-Item.

    Args:
        stac_item: The STAC item file/object to modify. Must be a STACObject.
        base_item: x

    Returns:
        (...): A pystac.item.Item object with the desired changes."""

    stac_item_dict = copy.deepcopy(stac_item.to_dict(include_self_link=False))

    assets_new = dict()
    for key in stac_item_dict["assets"]:
        asset = copy.deepcopy(stac_item_dict["assets"][key])
        for property in stac_item_dict["assets"][key]:
            if property.startswith("file:"):
                del asset[property]

        assets_new[key] = asset

    if base_item:
        try:
            for key in base_item["assets"]:
                if key not in assets_new:
                    assets_new[key] = copy.deepcopy(stac_item_dict["assets"][key])
                for property in base_item["assets"][key]:
                    assets_new[key][property] = copy.deepcopy(base_item["assets"][key][property])
                if "resolution" in assets_new[key]:
                    del assets_new[key]["resolution"]

        except Exception as e:
            __log.error("ERROR: %s" % e)

    stac_item_dict["assets"] = assets_new

    info = get_scene_id_info(stac_item.id)
    tby_item_id = (
        f"{info['sensor']}_{info['instrument']}_{info['processingLevel']}_{info['product']}_"
        f"{info['start']}_{info['stop']}_{info['instance']}"
    )
    stac_item_dict["properties"]["terrabyte:uniq_id"] = tby_item_id

    if "s3:productType" in stac_item_dict["properties"]:
        stac_item_dict["properties"]["s3:product_type"] = stac_item_dict["properties"]["s3:productType"]
        del stac_item_dict["properties"]["s3:productType"]

    info = stac_item_dict["id"].split("_")
    timeliness = info[-2]
    baseline_collection = info[-1]
    stac_item_dict["properties"]["s3:processing_timeliness"] = timeliness
    stac_item_dict["properties"]["s3:baseline_collection"] = baseline_collection
    stac_item_object_final = pystac.Item.from_dict(stac_item_dict)
    return stac_item_object_final
