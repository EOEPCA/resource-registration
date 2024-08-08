import shapely


def wkt_to_geom(wkt):
    return shapely.wkt.loads(wkt)


def geom_to_wkt(geom):
    return shapely.geometry.shape(geom).wkt


def calculate_bbox(geom):
    return shapely.geometry.shape(geom).bounds
