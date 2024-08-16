import duckdb


def get_max_datetime_from_geoparquet(geoparquet, column):
    """
    Description...

    Parameters:
        geoparquet: x
        column: x

    Returns:
        (...): ...
    """
    res = duckdb.query(f"set TimeZone = 'UTC'; SELECT max(\"{column}\") as max_datetime FROM '{geoparquet}'")
    return res.df().values[0][0].isoformat()
