import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from pypgstac.pypgstac import PgstacCLI


def get_items_from_query(dsn, order_id, collections, where_query):
    """
    Description...

    Parameters:
        dsn: x
        order_id: x
        collections: x
        where_query: x

    Returns:
        (...): ...
    """
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if len(collections) > 0:
        where_query += " and collection in (%s)" % (json.dumps(collections).replace('"', "'")[1:-1])

    _ = update_database(cur, conn, order_id, where_query, order_status="pending")
    scenes = get_items_from_order_id(order_id, collections, dsn)
    return scenes


def get_last_items_from_collection(dsn, order_id, collection, max_items=1000):
    """
    Description...

    Parameters:
        dsn: x
        order_id: x
        collection: x
        max_items: x

    Returns:
        (...): ...
    """
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    where_query = (
        "collection = '%s' and content->'properties'->>'order:status'='orderable' ORDER BY datetime DESC LIMIT %s"
        % (collection, max_items)
    )

    _ = update_database(cur, conn, order_id, where_query, order_status="pending")
    scenes = get_items_from_order_id(order_id, [collection], dsn)
    return scenes


def generate_batches_from_inventory(order_id, dsn, collections, where_query, batch_size=1000):
    """
    Description...

    Parameters:
        order_id: x
        dsn: x
        collections: x
        where_query: x
        batch_size: x

    Returns:
        (...): ...
    """
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()

    batches = []
    if len(collections) > 0:
        where_query += " and collection in (%s)" % (json.dumps(collections).replace('"', "'")[1:-1])

    print("Where query: " + where_query)
    order_no = 1
    batch_id = "%s_%s" % (order_id, order_no)

    affected_rows = update_database(cur, order_id, batch_id, where_query, batch_size)
    conn.commit()
    if affected_rows == 0:
        print("No scenes found")
        return []
    batches.append(batch_id)
    while affected_rows == batch_size:
        order_no += 1
        batch_id = "%s_%s" % (order_id, order_no)
        affected_rows = update_database(cur, order_id, batch_id, where_query, batch_size)
        conn.commit()
        batches.append(batch_id)

    conn.close()

    return batches


def update_database(cur, conn, order_id, where_query, order_status="ordered"):
    """
    Description...

    Parameters:
        cur: x
        conn: x
        order_id: x
        where_query: x
        order_status: x

    Returns:
        (...): ...
    """
    # Update all items with order id, order date, batch id, and ordered status
    order_update = {"order:status": order_status, "order:id": order_id, "order:date": datetime.now().isoformat()}
    query = (
        "UPDATE items "
        "SET content = jsonb_set(content, '{properties}', content->'properties' || '%s'::jsonb) "
        "WHERE id in (SELECT id FROM items WHERE %s);" % (json.dumps(order_update), where_query)
    )
    print(query)
    cur.execute(query)
    conn.commit()
    print("affected rows: %s" % cur.rowcount)
    return cur.rowcount


def update_database_batch(cur, conn, order_id, batch_id, where_query, batch_size):
    """
    Description...

    Parameters:
        cur: x
        conn: x
        order_id: x
        batch_id: x
        where_query: x
        batch_size: x

    Returns:
        (...): ...
    """
    # Update all items with order id, order date, batch id, and ordered status
    order_update = {
        "order:status": "ordered",
        "order:id": order_id,
        "order:date": datetime.now().isoformat(),
        "order:batch_id": batch_id,
    }
    query = (
        "UPDATE items "
        "SET content = jsonb_set(content, '{properties}', content->'properties' || '%s'::jsonb) "
        "WHERE id in (SELECT id FROM items WHERE %s LIMIT %s);" % (json.dumps(order_update), where_query, batch_size)
    )
    print(query)
    cur.execute(query)
    conn.commit()
    print("affected rows: %s" % cur.rowcount)
    return cur.rowcount


def get_order_from_id(scene_id, dsn):
    """
    Description...

    Parameters:
        scene_id: x
        dsn: x

    Returns:
        (...): ...
    """
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    query = "select content->'properties'->'terrabyte:order' from items where id='%s';" % scene_id
    print(query)
    cur.execute(query)
    scene = cur.fetchone()
    if len(scene) > 0:
        return scene[0]
    else:
        return scene


def get_items_from_order_id(order_id, collections, dsn):
    """
    Description...

    Parameters:
        order_id: x
        collections: x
        dsn: x

    Returns:
        (...): ...
    """
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if len(collections) > 0:
        where_query_add = "and collection in (%s)" % (str(collections).replace("[", "").replace("]", ""))
    query = (
        "select content->'properties'->'terrabyte:order' from items where content->'properties'->>'order:id'='%s' %s;"
        % (order_id, where_query_add)
    )
    print(query)
    cur.execute(query)
    result = cur.fetchall()
    scenes = [r[0] for r in result]
    return scenes


def insert_into_database(dsn, stac, method="insert_ignore"):
    """
    Description...

    Parameters:
        dsn: x
        stac: x
        method: x

    Returns:
        (...): ...

    Raises:
        Exception: ...
    """
    try:
        cli = PgstacCLI(dsn=dsn, debug=True)
        cli.load(table="items", file=stac, method=method)
        return True
    except Exception as e:
        print(str(e))
        return False


def get_scenes_from_batch(batch_id, collections, dsn):
    """
    Description...

    Parameters:
        batch_id: x
        collections: x
        dsn: x

    Returns:
        (...): ...
    """
    # Query scenes from a specific batch id, additional use filter through collections for performance reasons
    collections = json.dumps(collections).replace('"', "'")[1:-1]
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    query = "SELECT * FROM items WHERE content->'properties'->'order:batch_id' = '\"%s\"' and collection in (%s)" % (
        batch_id,
        collections,
    )
    print(query)
    cur.execute(query)
    scenes = cur.fetchall()

    # For all scenes set order status = "pending"
    status = "pending"
    query = (
        "UPDATE items "
        "SET content = jsonb_set(content, '{properties,order:status}', '\"%s\"'::jsonb) "
        "WHERE content->'properties'->'order:batch_id' = '\"%s\"' and collection in (%s);"
        % (status, batch_id, collections)
    )
    print(query)
    cur.execute(query)
    conn.commit()

    conn.close()
    return scenes


def update_items_inventory_status(property, id, collection, dsn, status="pending"):
    """
    Description...

    Parameters:
        property: x
        id: x
        collection: x
        dsn: x
        status: x

    """
    # property = 'order:order_id' or 'order:batch_id'

    collections = json.dumps(collection).replace('"', "'")[1:-1]
    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # For all scenes set order status = "pending"
    query = (
        "UPDATE items "
        "SET content = jsonb_set(content, '{properties,order:status}', '\"%s\"'::jsonb) "
        "WHERE content->'properties'->'%s' = '\"%s\"' and collection in (%s);" % (property, status, id, collections)
    )

    print(query)
    cur.execute(query)
    conn.commit()
    conn.close()
