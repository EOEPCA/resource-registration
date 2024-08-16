import earthaccess
import pystac
import os
from dateutil.parser import parse
from ..datasets.modis import get_scene_id_folder
from ..base.geometry import calculate_bbox


def login(username=None, password=None):
    """
    Description...

    Parameters:
        username: x
        password: x

    Returns:
        (...): ...
    """
    return earthaccess.login()


def search_data(short_name, version, count=-1, **kwargs):
    """
    Description...

    Parameters:
        short_name: x
        version: x
        count: x
        **kwargs: x

    Returns:
        (...): ...
    """
    results = earthaccess.search_data(
        short_name=short_name,
        version=version,
        # updated_since="2023-08-13T04:00:00.00Z",
        count=count,
        **kwargs,
    )
    return results


def search_scenes_ingestion(products, date_from, date_to=None):
    """
    Description...

    Parameters:
        products: x
        date_from: x
        date_to: x

    Returns:
        (...): ...
    """
    scenes = []
    for product in products:
        short_name, version = product.split(".")
        if "MODD10" in product or "MYD10" in product:
            version = version.replace("0", "")

        if date_to:
            p_scenes = search_data(short_name, version, production_date=(date_from, date_to))
        else:
            p_scenes = search_data(short_name, version, updated_since=date_from)
        scenes.extend(p_scenes)

    return scenes


def get_inventory_collection(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...
    """
    # scene_id = 'MOD09GA.A2023255.h08v08.061.2023257025446'
    parts = scene_id.split(".")
    return "modis-%s-%s" % (parts[0].lower(), parts[3])


def get_collection_name(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...
    """
    parts = scene_id.split(".")
    product = parts[0].lower()[3:]
    return "modis-%s-%s" % (product, parts[3])


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


def to_inventory(scene, order_status="orderable", order_id=None, batch_id=None):
    """
    Description...

    Parameters:
        scene: x
        order_status: x
        order_id: x
        batch_id: x

    Returns:
        (...): ...

    Raises:
        Exception: Could not find identifier.
    """
    item_id = scene["meta"]["native-id"]
    if item_id.startswith("SC"):
        for identifier in scene["umm"]["DataGranule"]["Identifiers"]:
            if identifier["IdentifierType"] == "ProducerGranuleId":
                item_id = identifier["Identifier"]
        if item_id is None:
            raise Exception("Could not find identifier")
        item_id = os.path.splitext(item_id)[0]
    item_parts = item_id.split(".")

    tby_parts = item_id.split(".")
    tby_parts.pop(-1)
    tby_item_id = ".".join(tby_parts)

    item_datetime_begin = parse(scene["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"])
    item_datetime_end = parse(scene["umm"]["TemporalExtent"]["RangeDateTime"]["EndingDateTime"])

    item_geometry = get_geometry(
        scene["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]["GPolygons"][0]["Boundary"]["Points"]
    )
    item_bbox = calculate_bbox(item_geometry)

    item = pystac.Item(
        id=item_id,
        datetime=None,
        start_datetime=item_datetime_begin,
        end_datetime=item_datetime_end,
        geometry=item_geometry,
        bbox=item_bbox,
        properties={},
    )

    item.properties["modis:scene_id"] = item_id

    item.properties["deprecated"] = False
    if order_status is not None:
        item.properties["order:status"] = order_status
    if order_id:
        item.properties["order:id"] = order_id
    if batch_id:
        item.properties["order:batch_id"] = batch_id
    item.properties["version"] = item_parts[-1]

    if "revision-date" in scene["meta"]:
        item.properties["modis:revision-date"] = parse(scene["meta"]["revision-date"]).isoformat()
    if "revision-id" in scene["meta"]:
        item.properties["modis:revision-id"] = scene["meta"]["revision-id"]
    item.properties["modis:provider-id"] = scene["meta"]["provider-id"]
    item.properties["modis:concept-id"] = scene["meta"]["concept-id"]

    for attrib in scene["umm"]["AdditionalAttributes"]:
        if attrib["Name"] == "VERTICALTILENUMBER":
            item.properties["modis:vertical-tile"] = int(attrib["Values"][0])
        elif attrib["Name"] == "HORIZONTALTILENUMBER":
            item.properties["modis:horizontal-tile"] = int(attrib["Values"][0])
        elif attrib["Name"] == "PROCESSVERSION":
            item.properties["modis:processor-version"] = attrib["Values"][0]

    item.properties["file:size"] = scene["umm"]["DataGranule"]["ArchiveAndDistributionInformation"][0]["Size"]
    item.properties["file:unit"] = scene["umm"]["DataGranule"]["ArchiveAndDistributionInformation"][0]["SizeUnit"]

    item.properties["terrabyte:item_id"] = tby_item_id
    item.properties["terrabyte:folder"] = os.path.join(get_scene_id_folder(item_id), item_id + ".hdf")
    item.properties["terrabyte:collection_id"] = get_collection_name(item_id)

    item.collection_id = get_inventory_collection(item_id)

    item.properties["modis:dates"] = dict()
    for date in scene["umm"]["ProviderDates"]:
        item.properties["modis:dates"][date["Type"]] = parse(date["Date"]).isoformat()

    for url in scene["umm"]["RelatedUrls"]:
        if url["Type"] == "GET DATA":
            item.assets["hdf"] = pystac.Asset(href=url["URL"])
        elif ".xml" in url["URL"] and "https://" in url["URL"]:
            item.assets["xml"] = pystac.Asset(href=url["URL"])

    item.properties["terrabyte:order"] = dict(
        scene_id=item.id,
        inventory=item.collection_id,
        collection=item.properties["terrabyte:collection_id"],
        download_folder=get_scene_id_folder(item_id),
        url_hdf=item.assets["hdf"].href,
        url_xml=item.assets["xml"].href,
    )

    return item
