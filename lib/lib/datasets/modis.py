import os
import json
import re
from datetime import datetime
import pystac
import rio_stac

from ..resources.stac import (
    extract_stactools,
    add_asset_filesize,
)

scene_id_pattern = (
    r"^"
    r"(?P<product>[0-9A-Z]{7,8})."
    r"A"
    r"(?P<start>[0-9]{7})."
    r"(?P<tile_id>[0-9a-z]{6})."
    r"(?P<version>[0-9]{3})."
    r"(?P<date_production>[0-9]{13})$"
)

folder_structure = "{sensor}/{product}.{version}/{year}/{month}/{day}/{tile_id}"
usgs_path_structure = "{usgs_path}/{product}.{version}/{year}.{month}.{day}"


def get_scene_id_info(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...
    """
    match = re.match(re.compile(scene_id_pattern), scene_id)
    variables = match.groupdict()
    date = datetime.strptime(variables["start"], "%Y%j")
    variables["year"] = date.strftime("%Y")
    variables["month"] = date.strftime("%m")
    variables["day"] = date.strftime("%d")

    if "product" in variables:
        if variables["product"].startswith("MOD"):
            variables["satellite"] = "Terra"
            variables["usgs_path"] = "https://e4ftl01.cr.usgs.gov/MOLT"
        elif variables["product"].startswith("MYD"):
            variables["satellite"] = "Aqua"
            variables["usgs_path"] = "https://e4ftl01.cr.usgs.gov/MOLA"
        else:
            variables["satellite"] = "Terra+Aqua"
            variables["usgs_path"] = "https://e4ftl01.cr.usgs.gov/MOTA"
        if variables["product"].startswith("VNP"):
            variables["sensor"] = "VIIRS"
            variables["usgs_path"] = None
        else:
            variables["sensor"] = "MODIS"
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
    # date = datetime.strptime(variables["start"], "%Y%j")
    # variables["year"] = date.strftime("%Y")
    # variables["month"] = date.strftime("%m")
    # variables["day"] = date.strftime("%d")

    if folder_format is None:
        folder_format = folder_structure
    return folder_format.format(**variables)


def get_usgs_path(scene_id):
    """
    Description...

    Parameters:
        scene_id: x

    Returns:
        (...): ...
    """
    return get_scene_id_folder(scene_id, folder_format=usgs_path_structure)


def get_stac_proj(input_file):
    """
    Description...

    Parameters:
        input_file: x

    Returns:
        (...): ...
    """
    rio = rio_stac.create_stac_item(input_file, with_proj=True)
    del rio.properties["proj:projjson"]
    return rio.properties


def create_stac_item(scene_path, scene_id, return_pystac=False, add_file_size=False):
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

    stac_function = "stactools.modis.stac.create_item"
    try:
        stac_file = os.path.join(os.path.dirname(scene_path), scene_id + ".STAC.json")
        stac_item = extract_stactools(scene_path, stac_function, {})
        stac_item = add_modis_adjustments(stac_item)

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
            with open(stac_file, "w") as f:
                f.write(json.dumps(stac_item.to_dict()))
            return stac_file

    except Exception as e:
        metadata_error = "Error during creating metadata for %s: %s" % (
            scene_path,
            str(e),
        )
        raise Exception("metadata_error: %s" % metadata_error)

    return stac_file


def add_modis_adjustments(stac):
    """
    Description...

    Parameters:
        stac: x

    Returns:
        (...): ...
    """
    product = os.path.basename(stac.id)[3:7].lower()
    asset_tmpl_file = "modis.%s.json" % product
    asset_tmpl = json.load(open(os.path.join(os.path.dirname(__file__), "templates", asset_tmpl_file)))
    data = stac.to_dict()

    data["properties"]["proj:wkt2"] = (
        'PROJCRS["unnamed",'
        'BASEGEOGCRS["Unknown datum based upon the custom spheroid",'
        'DATUM["Not specified (based on custom spheroid)",'
        'ELLIPSOID["Custom spheroid",6371007.181,0,LENGTHUNIT["metre",1,ID["EPSG",9001]]]],'
        'PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]]],'
        'CONVERSION["Sinusoidal",METHOD["Sinusoidal"],PARAMETER["Longitude of natural origin",0,'
        'ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],'
        'PARAMETER["False easting",0,LENGTHUNIT["metre",1],ID["EPSG",8806]],'
        'PARAMETER["False northing",0,LENGTHUNIT["metre",1],ID["EPSG",8807]]],'
        'CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT["Meter",1]],'
        'AXIS["(N)",north,ORDER[2],LENGTHUNIT["Meter",1]]]'
    )
    hdf = data["assets"]["hdf"]["href"]
    data["assets"]["hdf"]["type"] = "application/hdf4"
    if asset_tmpl_file == "modis.09ga.json":
        infos = dict()
        proj_1km = 'HDF4_EOS:EOS_GRID:"' + hdf + '":MODIS_Grid_1km_2D:num_observations_1km'
        infos["1km"] = get_stac_proj(proj_1km)
        proj_500m = 'HDF4_EOS:EOS_GRID:"' + hdf + '":MODIS_Grid_500m_2D:num_observations_500m'
        try:
            infos["500m"] = get_stac_proj(proj_500m)
        except Exception as e:
            print(data["id"], "FAILED", str(e))
            return False
        for asset in asset_tmpl:
            asset_tmpl[asset]["href"] = asset_tmpl[asset]["href"].replace("{{hdf_path}}", hdf)
            info = infos["500m"]
            if "1km" in asset_tmpl[asset]["href"]:
                info = infos["1km"]
            asset_tmpl[asset]["proj:transform"] = info["proj:transform"]
            asset_tmpl[asset]["proj:shape"] = info["proj:shape"]
        data["properties"]["proj:geometry"] = info["proj:geometry"]
        data["properties"]["proj:bbox"] = info["proj:bbox"]
        data["assets"].update(asset_tmpl)
    else:
        data["assets"].update(asset_tmpl)
        first_band = asset_tmpl[list(asset_tmpl.keys())[0]]["href"].replace("{{hdf_path}}", hdf)
        try:
            info = get_stac_proj(first_band)
        except Exception as e:
            print(data["id"], "FAILED", str(e))
            return False
        data["properties"].update(info)

    if "https://stac-extensions.github.io/projection/v1.1.0/schema.json" not in data["stac_extensions"]:
        data["stac_extensions"].append("https://stac-extensions.github.io/projection/v1.1.0/schema.json")

    stac_string = json.dumps(data)
    stac_string = stac_string.replace("{{hdf_path}}", hdf)
    stac_item = json.loads(stac_string)
    return pystac.Item.from_dict(stac_item)
