from dateutil.parser import parse
import pystac
import os
import re
from datetime import datetime

from ..resources.stac import (
    extract_stactools,
    add_asset_filesize,
)

scene_id_pattern = (
    r"^"
    r"(?P<product>[0-9A-Z]{7})."
    r"A"
    r"(?P<start>[0-9]{7})."
    r"(?P<tile_id>[0-9a-z]{6})."
    r"(?P<version>[0-9]{3})."
    r"(?P<date_production>[0-9]{13})"
)

scene_id_pattern2 = (
    r"^"
    r"(?P<product>[0-9A-Z]{8})."
    r"A"
    r"(?P<start>[0-9]{7})."
    r"(?P<tile_id>[0-9a-z]{6})."
    r"(?P<version>[0-9]{3})."
    r"(?P<date_production>[0-9]{13})"
)

folder_structure = "{product}.{version}/{year}/{month}/{day}/{tile_id}"


def get_scene_id_info(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...
    """
    used_pattern = scene_id_pattern
    if len(scene_id.split(".")[0]) == 8:
        used_pattern = scene_id_pattern2
    match = re.match(re.compile(used_pattern), scene_id)
    variables = match.groupdict()
    return variables


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
    date = datetime.strptime(variables["start"], "%Y%j")
    variables["year"] = date.strftime("%Y")
    variables["month"] = date.strftime("%m")
    variables["day"] = date.strftime("%d")

    if folder_format is None:
        folder_format = folder_structure
    return folder_format.format(**variables)


def viirs_metadata(scene_path, scene_id, return_pystac=False, add_file_size=False):
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
        Exception: Metadata_error: Error during creating metadata.
    """
    if scene_path[-1] == "/":
        scene_path = scene_path[:-1]

    if not os.path.exists(scene_path):
        raise Exception("metadata_error: Folder does not exist %s" % (scene_path))

    stac_function = "stactools.viirs.stac.create_item"
    try:
        stac_file = os.path.join(os.path.dirname(scene_path), scene_id + ".STAC.json")
        stac_item = extract_stactools(scene_path, stac_function, {})
        # stac_item = add_modis_adjustments(stac_item)

        stac_item.properties["terrabyte:uniq_id"] = ".".join(stac_item.id.split(".")[0:-1])
        stac_item.id = scene_id

        # Add file:// protocol for local file paths
        for asset in stac_item.assets:
            stac_item.assets[asset].href = "file://%s" % stac_item.assets[asset].href

        if add_file_size:
            stac_item = add_asset_filesize(stac_item)
        if return_pystac:
            return stac_item
        else:
            stac_item.save_object(dest_href=stac_file)
            return stac_file

    except Exception as e:
        metadata_error = "Error during creating metadata for %s: %s" % (
            scene_path,
            str(e),
        )
        raise Exception("metadata_error: %s" % metadata_error)

    return stac_file


def get_geometry(points):
    """
    Description...

    Parameters:
        points: x

    Returns:
        (...): ...
    """
    coordinates = []
    for p in points[::-1]:
        coordinates.append([p["Longitude"], p["Latitude"]])
    return {"type": "Polygon", "coordinates": [coordinates]}


def get_bbox(geometry):
    """
    Description...

    Parameters:
        geometry: x

    Returns:
        (...): ...

    Raises:
        Exception: No collection found.
    """
    coords = geometry["coordinates"]
    lats = [c[1] for c in coords[0]]
    lons = [c[0] for c in coords[0]]
    return [min(lons), min(lats), max(lons), max(lats)]


def create_item_for_inventory(scene, collection, collection_public):
    """
    Description...

    Parameters:
        scene: x
        collection: x
        collection_public: x

    Returns:
        (...): ...

    Raises:
        Exception: Could not find identifier.
    """
    item_id = None
    for identifier in scene["umm"]["DataGranule"]["Identifiers"]:
        if identifier["IdentifierType"] == "ProducerGranuleId":
            item_id = identifier["Identifier"]
    if item_id is None:
        raise Exception("Could not find identifier")
    item_id = os.path.splitext(item_id)[0]
    # item_id = scene['meta']['native-id']
    item_parts = item_id.split(".")

    tby_item_id = ".".join(item_parts[0:4])

    item_datetime_begin = parse(scene["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"])
    item_datetime_end = parse(scene["umm"]["TemporalExtent"]["RangeDateTime"]["EndingDateTime"])

    item_geometry = get_geometry(
        scene["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]["GPolygons"][0]["Boundary"]["Points"]
    )
    item_bbox = get_bbox(item_geometry)

    item = pystac.Item(
        id=item_id,
        datetime=None,
        start_datetime=item_datetime_begin,
        end_datetime=item_datetime_end,
        geometry=item_geometry,
        bbox=item_bbox,
        collection=collection,
        properties={},
    )

    item.properties["deprecated"] = False
    item.properties["order:status"] = "orderable"
    item.properties["version"] = item_parts[-1]

    if "revision-date" in scene["meta"]:
        item.properties["viirs:revision-date"] = parse(scene["meta"]["revision-date"]).isoformat()
    if "revision-id" in scene["meta"]:
        item.properties["viirs:revision-id"] = scene["meta"]["revision-id"]
    item.properties["viirs:provider-id"] = scene["meta"]["provider-id"]
    item.properties["viirs:concept-id"] = scene["meta"]["concept-id"]

    item.properties["platform"] = scene["umm"]["Platforms"][0]["ShortName"]

    for attrib in scene["umm"]["AdditionalAttributes"]:
        if attrib["Name"] == "VERTICALTILENUMBER":
            item.properties["viirs:vertical-tile"] = int(attrib["Values"][0])
        elif attrib["Name"] == "HORIZONTALTILENUMBER":
            item.properties["viirs:horizontal-tile"] = int(attrib["Values"][0])

    item.properties["file:size"] = scene["umm"]["DataGranule"]["ArchiveAndDistributionInformation"][0]["Size"]
    item.properties["file:unit"] = scene["umm"]["DataGranule"]["ArchiveAndDistributionInformation"][0]["SizeUnit"]

    item.properties["terrabyte:item_id"] = tby_item_id
    item.properties["terrabyte:folder"] = os.path.join(get_scene_id_folder(item_id), item_id + ".h5")
    item.properties["terrabyte:collection_id"] = collection_public

    item.properties["viirs:dates"] = dict()
    for date in scene["umm"]["ProviderDates"]:
        item.properties["viirs:dates"][date["Type"]] = parse(date["Date"]).isoformat()

    for url in scene["umm"]["RelatedUrls"]:
        if url["Type"] == "GET DATA":
            item.assets["hdf"] = pystac.Asset(href=url["URL"])
        elif ".xml" in url["URL"] and "https://" in url["URL"]:
            item.assets["xml"] = pystac.Asset(href=url["URL"])

    return item
