import shapely


def wkt_to_geom(wkt):
    """
    Description...

    Parameters:
        wkt: x

    Returns:
        (...): ...
    """
    return shapely.wkt.loads(wkt)


def geom_to_wkt(geom):
    """
    Description...

    Parameters:
        geom: x

    Returns:
        (...): ...
    """
    return shapely.geometry.shape(geom).wkt


def calculate_bbox(geom):
    """
    Description...

    Parameters:
        geom: x

    Returns:
        (...): ...
    """
    return shapely.geometry.shape(geom).bounds
