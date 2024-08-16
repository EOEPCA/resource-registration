#!/usr/bin/env python
# ----------------------------------------------------------------------------
# NSIDC Data Download Script
#
# Copyright (c) 2022 Regents of the University of Colorado
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# Tested in Python 2.7 and Python 3.4, 3.6, 3.7, 3.8, 3.9
#
# To run the script at a Linux, macOS, or Cygwin command-line terminal:
#   $ python nsidc-data-download.py
#
# On Windows, open Start menu -> Run and type cmd. Then type:
#     python nsidc-data-download.py
#
# The script will first search Earthdata for all matching files.
# You will then be prompted for your Earthdata username/password
# and the script will download the matching files.
#
# If you wish, you may store your Earthdata username/password in a .netrc
# file in your $HOME directory and the script will automatically attempt to
# read this file. The .netrc file should have the following format:
#    machine urs.earthdata.nasa.gov login MYUSERNAME password MYPASSWORD
# where 'MYUSERNAME' and 'MYPASSWORD' are your Earthdata credentials.
#
# Instead of a username/password, you may use an Earthdata bearer token.
# To construct a bearer token, log into Earthdata and choose "Generate Token".
# To use the token, when the script prompts for your username,
# just press Return (Enter). You will then be prompted for your token.
# You can store your bearer token in the .netrc file in the following format:
#    machine urs.earthdata.nasa.gov login token password MYBEARERTOKEN
# where 'MYBEARERTOKEN' is your Earthdata bearer token.
#
from __future__ import print_function

# import queue
import base64
import getopt
import json

# import logging
import math
import netrc
import os.path
import ssl
import sys

# import threading
import time

try:
    from urllib.parse import urlparse
    from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
    from urllib.error import HTTPError, URLError
except ImportError:
    from urlparse import urlparse
    from urllib2 import (
        urlopen,
        Request,
        HTTPError,
        URLError,
        build_opener,
        HTTPCookieProcessor,
    )

short_name = "MOD10A1"
version = "61"
time_start = "2000-02-24T00:00:00Z"
time_end = "2022-01-31T20:06:01Z"
bounding_box = ""
polygon = ""
filename_filter = ""
url_list = []

CMR_URL = "https://cmr.earthdata.nasa.gov"
URS_URL = "https://urs.earthdata.nasa.gov"
CMR_PAGE_SIZE = 2000
CMR_FILE_URL = (
    "{0}/search/granules.json?"
    "sort_key[]=start_date&sort_key[]=producer_granule_id"
    "&scroll=true&page_size={1}".format(CMR_URL, CMR_PAGE_SIZE)
)


def get_login_credentials():
    """
    Get user credentials from .netrc or prompt for input.

    Returns:
        (tuple): ...
    """
    credentials = None
    token = None

    try:
        info = netrc.netrc()
        username, account, password = info.authenticators(urlparse(URS_URL).hostname)
        if username == "token":
            token = password
        else:
            credentials = "{0}:{1}".format(username, password)
            credentials = base64.b64encode(credentials.encode("ascii")).decode("ascii")
    except Exception:
        username = None
        password = None

    return credentials, token


def build_version_query_params(version):
    """
    Description...

    Parameters:
        version: x

    Returns:
        (...): ...
    """
    desired_pad_length = 3
    if len(version) > desired_pad_length:
        print('Version string too long: "{0}"'.format(version))
        quit()

    version = str(int(version))  # Strip off any leading zeros
    query_params = ""

    while len(version) <= desired_pad_length:
        padded_version = version.zfill(desired_pad_length)
        query_params += "&version={0}".format(padded_version)
        desired_pad_length -= 1
    return query_params


def filter_add_wildcards(filter):
    """
    Description...

    Parameters:
        filter: x

    Returns:
        (...): ...
    """
    if not filter.startswith("*"):
        filter = "*" + filter
    if not filter.endswith("*"):
        filter = filter + "*"
    return filter


def build_filename_filter(filename_filter):
    """
    Description...

    Parameters:
        filename_filter: x

    Returns:
        (...): ...
    """
    filters = filename_filter.split(",")
    result = "&options[producer_granule_id][pattern]=true"
    for filter in filters:
        result += "&producer_granule_id[]=" + filter_add_wildcards(filter)
    return result


def build_cmr_query_url(
    provider,
    short_name,
    version,
    time_start,
    time_end,
    bounding_box=None,
    polygon=None,
    filename_filter=None,
):
    """
    Description...

    Parameters:
        provider: x
        short_name: x
        version: x
        time_start: x
        time_end: x
        bounding_box: x
        polygon: x
        filename_filter: x

    Returns:
        (...): ...
    """
    params = "&provider={0}".format(provider)
    params += "&short_name={0}".format(short_name)
    params += build_version_query_params(version)
    params += "&temporal[]={0},{1}".format(time_start, time_end)
    if polygon:
        params += "&polygon={0}".format(polygon)
    elif bounding_box:
        params += "&bounding_box={0}".format(bounding_box)
    if filename_filter:
        params += build_filename_filter(filename_filter)
    return CMR_FILE_URL + params


def get_speed(time_elapsed, chunk_size):
    """
    Description...

    Parameters:
        time_elapsed: x
        chunk_size: x

    Returns:
        (...): ...
    """
    if time_elapsed <= 0:
        return ""
    speed = chunk_size / time_elapsed
    if speed <= 0:
        speed = 1
    size_name = ("", "k", "M", "G", "T", "P", "E", "Z", "Y")
    i = int(math.floor(math.log(speed, 1000)))
    p = math.pow(1000, i)
    return "{0:.1f}{1}B/s".format(speed / p, size_name[i])


def output_progress(count, total, status="", bar_len=60):
    """
    Description...

    Parameters:
        count: x
        total: x
        status: x
        bar_len: x

    Returns:
        (...): ...
    """
    if total <= 0:
        return
    fraction = min(max(count / float(total), 0), 1)
    filled_len = int(round(bar_len * fraction))
    percents = int(round(100.0 * fraction))
    bar = "=" * filled_len + " " * (bar_len - filled_len)
    fmt = "  [{0}] {1:3d}%  {2}   ".format(bar, percents, status)
    print("\b" * (len(fmt) + 4), end="")  # clears the line
    sys.stdout.write(fmt)
    sys.stdout.flush()


def cmr_read_in_chunks(file_object, chunk_size=1024 * 1024):
    """
    Read a file in chunks using a generator. Default chunk size: 1Mb.

    Parameters:
        file_object: x
        chunk_size: x

    Returns:
        (...): ...
    """
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def get_login_response(url, credentials, token):
    """
    Description...

    Parameters:
        url: x
        credentials: x
        token: x

    Returns:
        (...): ...
    """
    opener = build_opener(HTTPCookieProcessor())

    req = Request(url)
    if token:
        req.add_header("Authorization", "Bearer {0}".format(token))
    elif credentials:
        try:
            response = opener.open(req)
            # We have a redirect URL - try again with authorization.
            url = response.url
        except HTTPError:
            # No redirect - just try again with authorization.
            pass
        except Exception as e:
            print("Error{0}: {1}".format(type(e), str(e)))
            sys.exit(1)

        req = Request(url)
        req.add_header("Authorization", "Basic {0}".format(credentials))

    try:
        response = opener.open(req)
    except HTTPError as e:
        err = "HTTP error {0}, {1}".format(e.code, e.reason)
        if "Unauthorized" in e.reason:
            if token:
                err += ": Check your bearer token"
            else:
                err += ": Check your username and password"
        print(err)
        sys.exit(1)
    except Exception as e:
        print("Error{0}: {1}".format(type(e), str(e)))
        sys.exit(1)

    return response


def cmr_download(urls, output_dir=".", force=False, quiet=False):
    """
    Download files from list of urls.

    Parameters:
        urls: x
        output_dir: x
        force: x
        quiet: x

    Returns:
        (...): ...
    """
    if not urls:
        return

    url_count = len(urls)
    if not quiet:
        print("Downloading {0} files...".format(url_count))
    credentials = None
    token = None

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for index, url in enumerate(urls, start=1):
        if not credentials and not token:
            p = urlparse(url)
            if p.scheme == "https":
                credentials, token = get_login_credentials()

        filename = url.split("/")[-1]
        filename = os.path.join(output_dir, filename)
        if not quiet:
            print("{0}/{1}: {2}".format(str(index).zfill(len(str(url_count))), url_count, filename))

        try:
            response = get_login_response(url, credentials, token)
            length = int(response.headers["content-length"])
            try:
                if not force and length == os.path.getsize(filename):
                    if not quiet:
                        print("  File exists, skipping")
                    continue
            except OSError:
                pass
            count = 0
            chunk_size = min(max(length, 1), 1024 * 1024)
            max_chunks = int(math.ceil(length / chunk_size))
            time_initial = time.time()
            with open(filename, "wb") as out_file:
                for data in cmr_read_in_chunks(response, chunk_size=chunk_size):
                    out_file.write(data)
                    if not quiet:
                        count = count + 1
                        time_elapsed = time.time() - time_initial
                        download_speed = get_speed(time_elapsed, count * chunk_size)
                        output_progress(count, max_chunks, status=download_speed)
            if not quiet:
                print()
        except HTTPError as e:
            print("HTTP error {0}, {1}".format(e.code, e.reason))
        except URLError as e:
            print("URL error: {0}".format(e.reason))
        except IOError:
            raise


# todo: function causes linter calls
# def download_data_threads(scenes, base_dir="."):
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
#
#     que = queue.Queue()
#     threads = []
#
#     # num_theads = min(50, len(scenes))
#     _ = min(50, len(scenes))
#
#     start = time.perf_counter()
#
#     for scene in scenes:
#         urls = scene["urls"]
#         file_dir = None
#         output_dir = os.path.join(base_dir, file_dir)
#
#         download_thread = threading.Thread(
#             target=lambda q, urls, output_dir: q.put(cmr_download(urls, output_dir)),
#             args=(que, urls, output_dir),
#         )
#         download_thread.start()
#         threads.append(download_thread)
#
#     while not q.empty():
#         work = q.get()  # fetch new work from the Queue
#         try:
#             data = urlopen(work[1]).read()
#             logging.info("Requested..." + work[1])
#             result[work[0]] = data  # Store data back at correct index
#         except:
#             logging.error("Error with URL check!")
#             result[work[0]] = {}
#         # signal to the queue that task has been processed
#         q.task_done()
#
#     for thread in threads:
#         thread.join()
#
#     download_time = time.perf_counter() - start
#
#     datasets = []
#     mean_download_speed = 0
#     while not que.empty():
#         result = que.get()
#         mean_download_speed += result["download_speed"]
#         datasets.append(result)
#
#     if len(datasets) > 0:
#         mean_download_speed = mean_download_speed / len(datasets)
#
#     return dict(
#         datasets=datasets,
#         total_time=download_time,
#         mean_download_speed=mean_download_speed,
#     )


def cmr_filter(search_results):
    """
    Select only the desired data files from CMR response.

    Parameters:
        search_results: x

    Returns:
        (...): ...
    """
    if "feed" not in search_results or "entry" not in search_results["feed"]:
        return []

    scenes = []

    for item in search_results["feed"]["entry"]:
        record = dict(
            id=item["id"],
            scene_id=item["producer_granule_id"],
            time_start=item["time_start"],
            time_end=item["time_end"],
            updated=item["updated"],
            granule_size=item["granule_size"],
            urls=[],
        )

        if "links" in item:
            unique_filenames = set()
            for link in item["links"]:
                if "href" not in link:
                    # Exclude links with nothing to download
                    continue
                if "inherited" in link and link["inherited"] is True:
                    # Why are we excluding these links?
                    continue
                if "rel" in link and "data#" not in link["rel"]:
                    # Exclude links which are not classified by CMR as "data" or "metadata"
                    continue

                if "title" in link and "opendap" in link["title"].lower():
                    # Exclude OPeNDAP links--they are responsible for many duplicates
                    # This is a hack; when the metadata is updated to properly identify
                    # non-datapool links, we should be able to do this in a non-hack way
                    continue

                filename = link["href"].split("/")[-1]
                if filename in unique_filenames:
                    # Exclude links with duplicate filenames (they would overwrite)
                    continue
                unique_filenames.add(filename)

                record["urls"].append(link["href"])

        scenes.append(record)

    return scenes


def cmr_search(
    provider,
    short_name,
    version,
    time_start,
    time_end,
    bounding_box="",
    polygon="",
    filename_filter="",
    quiet=False,
):
    """
    Perform a scrolling CMR query for files matching input criteria.

    Parameters:
        provider: x
        short_name: x
        version: x
        time_start: x
        time_end: x
        bounding_box: x
        polygon: x
        filename_filter: x
        quiet: x

    Returns:
        (...): ...
    """
    cmr_query_url = build_cmr_query_url(
        provoder=provider,
        short_name=short_name,
        version=version,
        time_start=time_start,
        time_end=time_end,
        bounding_box=bounding_box,
        polygon=polygon,
        filename_filter=filename_filter,
    )
    if not quiet:
        print("Querying for data:\n\t{0}\n".format(cmr_query_url))

    cmr_scroll_id = None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    scenes = []
    hits = 0
    while True:
        req = Request(cmr_query_url)
        if cmr_scroll_id:
            req.add_header("cmr-scroll-id", cmr_scroll_id)
        try:
            response = urlopen(req, context=ctx)
        except Exception as e:
            print("Error: " + str(e))
            sys.exit(1)
        if not cmr_scroll_id:
            # Python 2 and 3 have different case for the http headers
            headers = {k.lower(): v for k, v in dict(response.info()).items()}
            cmr_scroll_id = headers["cmr-scroll-id"]
            hits = int(headers["cmr-hits"])
            if not quiet:
                if hits > 0:
                    print("Found {0} matches.".format(hits))
                else:
                    print("Found no matches.")
        search_page = response.read()
        search_page = json.loads(search_page.decode("utf-8"))
        url_scroll_results = cmr_filter(search_page)
        if not url_scroll_results:
            break
        if not quiet and hits > CMR_PAGE_SIZE:
            print(".", end="")
            sys.stdout.flush()
        scenes += url_scroll_results

    if not quiet and hits > CMR_PAGE_SIZE:
        print()
    return scenes


def main(argv=None):
    """
    Description...

    Parameters:
        argv: x

    Returns:
        (...): ...
    """
    global short_name, version, time_start, time_end, bounding_box, polygon, filename_filter, url_list

    if argv is None:
        argv = sys.argv[1:]

    force = False
    quiet = False
    usage = "usage: nsidc-download_***.py [--help, -h] [--force, -f] [--quiet, -q]"

    try:
        opts, args = getopt.getopt(argv, "hfq", ["help", "force", "quiet"])
        for opt, _arg in opts:
            if opt in ("-f", "--force"):
                force = True
            elif opt in ("-q", "--quiet"):
                quiet = True
            elif opt in ("-h", "--help"):
                print(usage)
                sys.exit(0)
    except getopt.GetoptError as e:
        print(e.args[0])
        print(usage)
        sys.exit(1)

    try:
        if not url_list:
            url_list = cmr_search(
                short_name,
                version,
                time_start,
                time_end,
                bounding_box=bounding_box,
                polygon=polygon,
                filename_filter=filename_filter,
                quiet=quiet,
            )

        cmr_download(url_list, force=force, quiet=quiet)
    except KeyboardInterrupt:
        quit()


if __name__ == "__main__":
    main()
