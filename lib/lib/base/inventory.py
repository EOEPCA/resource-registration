import os
import duckdb
import requests
import psycopg2
from datetime import datetime

from .order import insert_into_database


def update_inventory(scene_id, collection, inventory_dsn):
    """
    Description...

    Parameters:
        scene_id: x
        collection: x
        inventory_dsn: x

    Returns:
        (...): ...

    Raises:
        Exception: 0 affected rows.
    """
    # Update inventory database
    print("Updating inventory for %s" % (scene_id))
    conn = psycopg2.connect(inventory_dsn)
    cur = conn.cursor()
    status = "succeeded"
    query = (
        # todo: define uniform format string rules (for entire project)
        # "UPDATE items SET content = jsonb_set(content, '{properties,order:status}', '\"%s\"'::jsonb)
        # WHERE id = '%s' and collection in ('%s');"
        "UPDATE items "
        "SET content = jsonb_set(content, '{properties,order:status}', '\"%s\"'::jsonb) "
        "WHERE id = '%s' "
        "AND collection in ('%s');" % (status, scene_id, collection)
    )

    print(query)
    cur.execute(query)
    print("[%s] affected rows: %s" % (scene_id, cur.rowcount))

    if cur.rowcount == 0:
        conn.close()
        raise Exception("0 affected rows")
    else:
        conn.commit()
        conn.close()
        return True


def get_scene_id_from_inventory_db(conn, collection, max_datetime=None):
    """
    Description...

    Parameters:
        conn: x
        collection: x
        max_datetime: x

    Returns:
        (list): ...
    """
    if max_datetime:
        query = (
            f"SELECT id "
            f"FROM items "
            f"WHERE collection='{collection}' "
            f"AND content->'properties'->>'order:status' != 'removed' "
            f"AND datetime < '{max_datetime}'"
        )
    else:
        query = (
            f"SELECT id "
            f"FROM items "
            f"WHERE collection='{collection}' "
            f"AND content->'properties'->>'order:status' != 'removed'"
        )
    print(query)
    cur = conn.cursor()
    cur.execute(query)
    return [i[0] for i in cur.fetchall()]


def get_scenes_from_inventory_file(db_file, date_column="ContentDate:Start", max_datetime=None):
    """
    Description...

    Parameters:
        db_file: x
        date_column: x
        max_datetime: x

    Returns:
        (...): ...
    """
    print(f"Query {db_file}")
    # if max_datetime:
    #     results = duckdb.query(
    #         'set TimeZone=\'UTC\'; SELECT * FROM \'%s\' WHERE "%s" < \'%s\'' % (db_file, date_column, max_datetime))
    # else:
    #     results = duckdb.query('set TimeZone=\'UTC\'; SELECT * FROM \'%s\'' % (db_file))
    # Todo: Check for quotes
    if max_datetime:
        results = duckdb.query(
            "set TimeZone='UTC'; SELECT * FROM '%s' WHERE '%s' < '%s'" % (db_file, date_column, max_datetime)
        )
    else:
        results = duckdb.query("set TimeZone='UTC'; SELECT * FROM '%s'" % (db_file))
    return results.df()


def get_scenes_diff(scenes_inventory, scenes_db, id_column):
    """
    Description...

    Parameters:
        scenes_inventory: x
        scenes_db: x
        id_column: x

    Returns:
        (tuple(...)): ...
    """
    # Inventory API does not include the file extension as part of the scene id column in comparison to the inventory
    # files from CDSE data provider. Thus, we need to remove the file extension from the inventory list of scene ids.
    file_ext = os.path.splitext(scenes_inventory[id_column][0])[1]
    scenes_inventory_names = list(scenes_inventory[id_column].str.replace(file_ext, ""))
    print(f"Scenes Inventory: {len(scenes_inventory_names)}")

    # Substract the scene ids of the terrabyte Inventory from the inventory of the data provider to get missing scenes
    new_scenes = list(set(scenes_inventory_names).difference(scenes_db))
    print(f"New items: {len(new_scenes)}")

    # Substract the inventory of the data provider from the terrabyte Inventory
    # to get scenes that should be removed (not anymore available)
    to_be_removed = list(set(scenes_db).difference(scenes_inventory_names))
    print(f"Items to be removed: {len(to_be_removed)}")
    return new_scenes, to_be_removed


def get_item_from_id(scene_id, collection, api_url="https://stac.terrabyte.lrz.de/inventory/api"):
    """
    Description...

    Parameters:
        scene_id: x
        collection: x
        api_url: x

    Returns:
        (...|bool): ...
    """
    url = f"{api_url}/collections/{collection}/items/{scene_id}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    else:
        return False


def query_geoparquet(
    inventory,
    collection,
    geoparquet,
    max_datetime=None,
    date_column="datetime",
    inventory_column="geoparquet",
    id_column="id",
):
    """
    Description...

    Parameters:
        inventory: x
        collection: x
        geoparquet: x
        max_datetime: x
        date_column: x
        inventory_column: x
        id_column: x

    Returns:
        (...): ...
    """
    if max_datetime:
        query = (
            f"set TimeZone = 'UTC'; "
            f'SELECT DATE_TRUNC(\'year\', "{date_column}") AS year, count("{id_column}") AS count '
            f"FROM '{geoparquet}' "
            f"WHERE \"{date_column}\" < '{max_datetime}' "
            f"GROUP by year"
        )
    else:
        query = (
            f"set TimeZone = 'UTC'; "
            f'SELECT DATE_TRUNC(\'year\', "{date_column}") AS year, count("{id_column}") AS count '
            f"FROM '{geoparquet}' "
            f"GROUP by year"
        )

    print(f"Geoparquet {collection}: {geoparquet}")
    print(f"Query: {query}")

    res = duckdb.query(query)
    df = res.df()

    # Convert year to integer and index
    df["year"] = df["year"].dt.year
    df.set_index("year", inplace=True)

    # Select count column
    data = df.to_dict()["count"]

    if collection not in inventory:
        inventory[collection] = dict()

    for year in data:
        if str(year) not in inventory[collection]:
            inventory[collection][str(year)] = dict(
                inventory=0, removed=0, online=0, pending=0, deprecated=0, stac_api=0, geoparquet=0, datasource=0
            )

        inventory[collection][str(year)][inventory_column] = data[year]

    return inventory


def query_stac_db(cur, inventory, collection, max_datetime=None):
    """
    Description...

    Parameters:
        cur: x
        inventory: x
        collection: x
        max_datetime: x

    Returns:
        (...): ...
    """
    where_condition = ""
    if max_datetime:
        where_condition = f"AND datetime < '{max_datetime}'"
    query = (
        f"SELECT DATE_TRUNC('year', datetime) AS year, count(id) "
        f"FROM items "
        f"WHERE collection='{collection}' {where_condition} "
        f"GROUP BY year;"
    )
    print(f"STAC API {collection}: {query}")

    cur.execute(query)
    api_stats = cur.fetchall()
    if collection not in inventory:
        inventory[collection] = dict()

    for i in api_stats:
        date, count = i
        year = str(date.year)

        if year not in inventory[collection]:
            inventory[collection][year] = dict(
                inventory=0, removed=0, online=0, pending=0, deprecated=0, stac_api=0, geoparquet=0, datasource=0
            )

        inventory[collection][year]["stac_api"] += count

    return inventory


def query_inventory_db(cur, inventory, collection, max_datetime=None):
    """
    Description...

    Parameters:
        cur: x
        inventory: x
        collection: x
        max_datetime: x

    Returns:
        (...): ...
    """
    where_condition = ""
    if max_datetime:
        where_condition = f"AND datetime < '{max_datetime}'"
    query = (
        f"SELECT DATE_TRUNC('year', datetime) AS year, "
        f"content->'properties'->>'order:status' AS status, "
        f"content->'properties'->>'deprecated' AS deprecated, count(id) "
        f"FROM items "
        f"WHERE collection='{collection}' {where_condition} "
        f"GROUP BY year, status, deprecated;"
    )
    print(f"Inventory {collection}: {query}")

    cur.execute(query)
    api_stats = cur.fetchall()

    if collection not in inventory:
        inventory[collection] = dict()

    for i in api_stats:
        date, status, deprecated, count = i
        year = str(date.year)

        if year not in inventory[collection]:
            inventory[collection][year] = dict(
                inventory=0, removed=0, online=0, pending=0, deprecated=0, stac_api=0, geoparquet=0, datasource=0
            )

        if status == "succeeded" and deprecated == "false":
            inventory[collection][year]["online"] += count
        elif status == "removed":
            inventory[collection][year]["removed"] += count
        elif status != "succeeded" and deprecated == "false":
            inventory[collection][year]["pending"] += count
        elif deprecated == "true":
            inventory[collection][year]["deprecated"] += count

        if status != "removed":
            inventory[collection][year]["inventory"] += count

    return inventory


def calculate_differences(collection, inventory_geoparquet, conn, id_column, date_column, max_datetime=None):
    """
    Description...

    Parameters:
        collection: x
        inventory_geoparquet: x
        conn: x
        id_column: x
        date_column: x
        max_datetime: x

    Returns:
        (tuple(...)): ...
    """
    scenes_inventory = get_scenes_from_inventory_file(
        inventory_geoparquet, date_column=date_column, max_datetime=max_datetime
    )
    scenes_db_names = get_scene_id_from_inventory_db(conn, collection, max_datetime=max_datetime)
    new_scenes, to_be_removed = get_scenes_diff(scenes_inventory, scenes_db_names, id_column)
    if len(new_scenes) > 0:
        scenes_inventory_by_name = scenes_inventory.set_index(id_column)
        file_ext = os.path.splitext(scenes_inventory[id_column][0])[1]
        scenes = []
        for scene_id in new_scenes:
            scene = scenes_inventory_by_name.loc[scene_id + file_ext].to_dict()
            scene[id_column] = scene_id + file_ext
            scenes.append(scene)
        return scenes, to_be_removed
    else:
        return new_scenes, to_be_removed


def generate_stac_new_scenes(scenes, collection, inventory_fct):
    """
    Description...

    Parameters:
        scenes: x
        collection: x
        inventory_fct: x

    Returns:
        (...): ...

    Raises:
        Exception: Error while creating metadata for a scene.
    """
    stac_items = []
    for scene in scenes:
        try:
            stac_items.append(inventory_fct(scene, collection).to_dict())
        except Exception as e:
            print(f"Error while creating metadata for {scene}: {e}")
    return stac_items


def import_new_scenes(scenes, collection, inventory_fct, dsn):
    """
    Description...

    Parameters:
        scenes: x
        collection: x
        inventory_fct: x
        dsn: x

    Returns:
        (...): ...
    """
    stac_items = generate_stac_new_scenes(scenes, collection, inventory_fct)
    return insert_into_database(dsn, stac_items)


def delete_removed_scenes(collection, to_be_removed, reasons, api_url, api_user, api_pw):
    """
    Description...

    Parameters:
        collection: x
        to_be_removed: x
        reasons: x
        api_url: x
        api_user: x
        api_pw: x
    """
    for scene_id in to_be_removed:
        stac_item = get_item_from_id(scene_id, collection)
        if stac_item:
            order_status = stac_item["properties"]["order:status"]
            print(scene_id, "Order Status: " + order_status)
            if order_status == "succeeded":
                # remove from STAC API
                r = requests.delete(
                    "%s/collections/%s/items/%s" % (api_url, collection, stac_item["id"]),
                    auth=(api_user, api_pw),
                )
                print("%s: Delete from STAC API: %s" % (scene_id, r.status_code))

            stac_item["properties"]["order:status"] = "removed"
            if scene_id in reasons:
                reason = reasons[scene_id]
                stac_item["properties"]["deletion:date"] = reason["DeletionDate"]
                stac_item["properties"]["deletion:cause"] = reason["DeletionCause"]
            stac_item["properties"]["deprecated"] = True
            stac_item["properties"]["updated"] = datetime.utcnow().isoformat() + "Z"
            r = requests.put(
                "%s/collections/%s/items/%s"
                % ("https://stac.terrabyte.lrz.de/inventory/api", collection, stac_item["id"]),
                json=stac_item,
                # auth=(api_user, api_pw)
            )
            print("%s: Update Inventory API: %s" % (scene_id, r.status_code))
        else:
            print("Not found in inventory: %s" % scene_id)
