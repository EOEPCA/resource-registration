import os
import itertools
from typing import Sequence
from concurrent.futures import ThreadPoolExecutor

from dateutil.parser import parse
from datetime import datetime, timedelta
import calendar

import pypgstac.db
import pypgstac.hydration
import pandas as pd
import shapely.wkb

import stac_geoparquet.arrow
import pyarrow as pa

BASE_QUERY = "SELECT * from pgstac.items WHERE collection='{}'"


def partition_from_db_items_pair(idx, db, collection, output, base_url, overwrite=True):
    """
    Description...

    Parameters:
        idx: x
        db: x
        collection: x
        output: x
        base_url: x
        overwrite: x

    Returns:
        (...): ...
    """
    try:
        start, end = idx
        file_end = end - timedelta(days=1)
        f_out = f"{output}/{start.strftime('%Y%m%d')}_{file_end.strftime('%Y%m%d')}.parquet"
        if os.path.exists(f_out) and not overwrite:
            print(start, end, "exists")
            return True
        print(start, end)
        query = BASE_QUERY.format(collection) + f" AND datetime >= '{start}' AND datetime < '{end}'"

        base_item = db.query_one(f"select * from collection_base_item('{collection}');")

        results = db.query(query)
        items = [prepare_item(result, base_item, base_url) for result in results]
        print(start, end, "items", len(items))
        if len(items) == 0:
            return None
        items_arrow = stac_geoparquet.arrow.parse_stac_items_to_arrow(items)
        table = pa.Table.from_batches(items_arrow)
        stac_geoparquet.arrow.to_parquet(table, f_out)
        print(start, end, f_out, ": OK")
        return f_out
    except Exception as e:
        print(start, end, "FAILED", str(e))


def pairwise(iterable: Sequence) -> list[tuple[datetime, datetime]]:
    """
    Description...

    Parameters:
        iterable: x

    Returns:
        (list): ...
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def prepare_datetime_pairs(datetime_range, partition_frequency):
    """
    Description...

    Parameters:
        datetime_range: x
        partition_frequency: x


    Returns:
        (list): ...
    """
    start_datetime = datetime.fromisoformat(datetime_range.split("/")[0].split("T")[0])
    end_datetime = datetime.fromisoformat(datetime_range.split("/")[1].split("T")[0])
    idx = pd.date_range(
        start_datetime - timedelta(weeks=5), end_datetime + timedelta(weeks=5), freq=partition_frequency
    )
    dt_pairs = pairwise(idx)
    return list(dt_pairs)


def prepare_item(record, base_item, base_url):
    """
    Description...

    Parameters:
        record: x
        base_item: x
        base_url: x

    Returns:
        (...): ...
    """
    columns = [
        "id",
        "geometry",
        "collection",
        "datetime",
        "end_datetime",
        "content",
    ]

    item = dict(zip(columns, record))
    item.pop("datetime")
    item.pop("end_datetime")

    geom = shapely.wkb.loads(item["geometry"], hex=True)

    item["geometry"] = geom.__geo_interface__
    content = item.pop("content")
    assert isinstance(content, dict)
    if "bbox" in content:
        item["bbox"] = content["bbox"]
    else:
        item["bbox"] = list(geom.bounds)

    item["assets"] = content["assets"]
    if "stac_extensions" in content:
        item["stac_extensions"] = content["stac_extensions"]
    item["properties"] = content["properties"]

    pypgstac.hydration.hydrate(base_item, item)

    item["links"] = [
        {
            "rel": "collection",
            "type": "application/json",
            "href": f"{base_url}/collections/{item['collection']}",
        },
        {
            "rel": "parent",
            "type": "application/json",
            "href": f"{base_url}/collections/{item['collection']}",
        },
        {
            "rel": "root",
            "type": "application/json",
            "href": f"{base_url}",
        },
        {
            "rel": "self",
            "type": "application/geo+json",
            "href": f"{base_url}/collections/{item['collection']}/items/{item['id']}",
        },
    ]

    return item


def generate_date_ranges(start_date, end_date):
    """
    Description...

    Parameters:
        start_date: x
        end_date: x


    Returns:
        (...): ...
    """
    date_ranges = []

    # Set the initial current_date to the start_date
    current_date = start_date

    while current_date <= end_date:
        year = current_date.year
        month = current_date.month

        # Determine the first day of the current month
        first_day_of_month = datetime(year, month, 1)
        # Determine the last day of the current month
        _, last_day_of_month = calendar.monthrange(year, month)
        last_day_of_month_date = datetime(year, month, last_day_of_month)

        # If the current_date is before the first day of the month, set it to the first day
        if current_date < first_day_of_month:
            current_date = first_day_of_month

        while current_date.month == month and current_date <= end_date:
            end_range_date = current_date + timedelta(days=7)

            # Ensure the end range date does not exceed the last day of the month or the end date
            if end_range_date > last_day_of_month_date:
                end_range_date = last_day_of_month_date
            if end_range_date > end_date:
                end_range_date = end_date

            date_ranges.append((current_date, end_range_date + timedelta(days=1)))

            # Move to the next range
            current_date = end_range_date + timedelta(days=1)

        # Move to the first day of the next month
        current_date = first_day_of_month + timedelta(days=32)
        current_date = datetime(current_date.year, current_date.month, 1)

    return date_ranges


def handle_partition_db_arrow(dsn, collection, output, base_url, frequency, datetime_range=None, max_threads=8):
    """
    Description...

    Parameters:
        dsn: x
        collection: x
        output: x
        base_url: x
        frequency: x
        datetime_range: x
        max_threads: x

    Returns:
        (...): ...
    """
    db = pypgstac.db.PgstacDB(dsn)
    with db:
        db.connection.execute("set statement_timeout = 600000;")

        if not datetime_range:
            dt_pairs = []
            collection_db = db.query_one(f"SELECT * FROM pgstac.collections WHERE id='{collection}'")
            interval = collection_db[2]["extent"]["temporal"]["interval"][0]
            start = parse(interval[0])
            end = interval[1]
            if not end:
                end = datetime.now(tz=start.tzinfo)
            else:
                end = parse(interval[1])
            datetime_range = f"{start.isoformat()}/{end.isoformat()}"
            interval_pairs = prepare_datetime_pairs(datetime_range, frequency)
            dt_pairs.extend(interval_pairs)

            # For weekly frequencies we calculate a 7 day rolling window starting on the first of each month
            if frequency == "W":
                start_date = datetime(start.year, start.month, 1)
                end_date = datetime(end.year, end.month, end.day)
                dt_pairs = generate_date_ranges(start_date, end_date)

        else:
            dt_pairs = prepare_datetime_pairs(datetime_range, frequency)

        executor = ThreadPoolExecutor(max_workers=max_threads)
        futures = [
            executor.submit(partition_from_db_items_pair, pair, db, collection, output, base_url) for pair in dt_pairs
        ]
        for f in futures:
            if res := f.result():
                print("Exported", res)
        print("End of processing")
