import psycopg2

def update_inventory(scene_id, collection, inventory_dsn):
    # Update inventory database
    print("Updating inventory for %s" % (scene_id))
    conn = psycopg2.connect(inventory_dsn)
    cur = conn.cursor()
    status = "succeeded"
    query = "UPDATE items SET content = jsonb_set(content, '{properties,order:status}', '\"%s\"'::jsonb) WHERE id = '%s' and collection in ('%s');" % (status, scene_id, collection)
    print(query)
    cur.execute(query)
    print("[%s] affected rows: %s" % (scene_id, cur.rowcount))
    
    if cur.rowcount == 0: 
        raise Exception("0 affected rows")
    else:
        conn.commit()
        return True