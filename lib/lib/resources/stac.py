import os
import json
import importlib
import datetime
import pystac
import requests
from pystac.extensions.file import FileExtension
from ..base.file import get_file_size, get_folder_size


def extract_by_function_name(scene_path: str, function_name: str, stac_function_options: dict):
    """
    Extract metadata from scene folder

    Arguments:
        scene_path: Scene folder to extract metadata from
        function_name: Function name for scene to be used for metadata extraction
                       (e.g., stactools.sentinel2.stac.create_item)
        stac_function_options: x

    Returns:
        (...): As defined in the function
    """
    if scene_path[-1] == "/":
        scene_path = scene_path[:-1]

    mod_name, func_name = function_name.rsplit(".", 1)
    mod = importlib.import_module(mod_name)
    metadata_function = getattr(mod, func_name)

    return metadata_function(scene_path, **stac_function_options)


def extract_stactools(scene_path: str, function_name: str, stac_function_options: dict):
    """
    Description...

    Parameters:
        scene_path: x
        function_name: x
        stac_function_options: x

    Returns:
        (...): ...
    """
    stac_item = extract_by_function_name(scene_path, function_name, stac_function_options)
    if "created" not in stac_item.properties:
        stac_item.properties["created"] = str(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    return stac_item


def extract_and_save_stactools(
    scene_path: str, function_name: str, stac_function_options: dict, output_file: str, make_asset_hrefs_relative=False
):
    """
    Description...

    Parameters:
        scene_path: x
        function_name: x
        stac_function_options: x
        output_file: x
        make_asset_hrefs_relative: x

    Returns:
        (...): ...

    Raises:
        Exception: Could not make asset hrefs relative.
    """
    # stactools packages return a pystac.Item as result
    stac_item = extract_by_function_name(scene_path, function_name, stac_function_options)
    if "created" not in stac_item.properties:
        stac_item.properties["created"] = str(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    if make_asset_hrefs_relative:
        try:
            if stac_item.get_self_href() is None:
                stac_item.set_self_href(output_file)

            stac_item = stac_item.make_asset_hrefs_relative()
            stac_item.remove_links("self")
        except Exception as e:
            print("Could not make asset hrefs relative: %s" % str(e))
    with open(output_file, "w") as file:
        file.write(json.dumps(stac_item.to_dict()))
    return output_file


def add_asset_filesize(stac):
    """
    Description...

    Parameters:
        stac: x

    Returns:
        (...): ...
    """
    # if not os.path.exists(stac_file):
    #    raise Exception("File %s does not exist!" % stac_file)
    # stac = pystac.Item.from_file(stac_file)
    FileExtension.add_to(stac)

    # base_dir = os.path.dirname(stac_file)

    for asset_key in stac.assets:
        asset = stac.assets[asset_key]
        # if asset.href[0] == '/':
        #    base_dir = ''
        # href = os.path.join(base_dir, asset.href)
        if os.path.isfile(asset.href):
            asset.extra_fields["file:size"] = get_file_size(asset.href)
        elif os.path.isdir(asset.href):
            asset.extra_fields["file:size"] = get_folder_size(asset.href)

    # stac.save_object(include_self_link=False)
    return stac


def register_metadata(
    stac_file,
    scene_id,
    inventory_id,
    inventory_collection,
    collection,
    api_url,
    api_user,
    api_pw,
    inventory_dsn,
    file_deletion=False,
):
    """
    Description...

    Parameters:
        stac_file: x
        scene_id: x
        inventory_id: x
        inventory_collection: x
        collection: x
        api_url: x
        api_user: x
        api_pw: x
        inventory_dsn: x
        file_deletion: x

    Returns:
        (...): ...

    Raises:
        Exception: Registration_error: STAC file does not exist.
        Exception: Registration_error: STAC collection not found in configuration or file.
        Exception: Registration_error: Request of product not successful.
    """
    stac_files = stac_file.split(";")
    for stac_file in stac_files:
        if not os.path.exists(stac_file):
            raise Exception(
                "registration_error: STAC file does not exist %s" % (stac_file),
            )
        stac = pystac.read_file(stac_file)
        stac = stac.make_asset_hrefs_absolute()
        stac.properties["terrabyte:scene_id"] = scene_id

        # Check STAC collection id
        if collection:
            stac.collection_id = collection  # stac.set_collection

        if stac.collection_id is None:
            raise Exception(
                "registration_error: STAC collection not found in configuration or file",
            )

        # Conduct request to STAC API
        api_action = "insert"
        r = requests.post(
            "%s/collections/%s/items" % (api_url, stac.collection_id), json=stac.to_dict(), auth=(api_user, api_pw)
        )
        if r.status_code == 409:
            # Product already exists -> update
            stac.properties["updated"] = str(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
            api_action = "update"
            r = requests.put(
                "%s/collections/%s/items/%s" % (api_url, stac.collection_id, stac.id),
                json=stac.to_dict(),
                auth=(api_user, api_pw),
            )

        if r.status_code != 200:
            raise Exception(
                (
                    "registration_error: %s request of product %s not successful. "
                    "Status code: %s. Reason: %s. Response content: %s"
                )
                % (api_action, stac.id, r.status_code, r.reason, r.content),
            )
        else:
            print("%s request of product %s in collection %s successful." % (api_action, stac.id, stac.collection_id))

        # Optionally, delete STAC file
        if file_deletion:
            os.remove(stac_file)

    return {}
