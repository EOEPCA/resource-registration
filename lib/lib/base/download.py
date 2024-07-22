import os
import time
import json
import requests
from .file import check_file_size

def download_data(
    url,
    output_dir,
    file_name=None,
    chunk_size=1024 * 1000,
    timeout=300,
    auth=None,
    check_size=True
):
    """
    Download single file from USGS M2M by download url
    """

    try:
        print("Waiting for server response...")
        if auth:
            r = requests.get(url, stream=True, allow_redirects=True, timeout=timeout, auth=auth)
        else:
            r = requests.get(url, stream=True, allow_redirects=True, timeout=timeout)
        expected_file_size = int(r.headers.get("content-length", -1))
        if file_name is None:
            try:
                file_name = r.headers["Content-Disposition"].split('"')[1]
            except Exception as e:
                raise Exception("Can not automatically identify file_name.")
        
        print(f"Filename: {file_name}")
        file_path = os.path.join(output_dir, file_name)
        # TODO: Check for existing files and whether they have the correct file size
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(file_path, "wb") as f:
            start = time.perf_counter()
            print(f"Download of {file_name} in progress...")
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
            duration = time.perf_counter() - start
        
        file_size = os.stat(file_path).st_size
        speed = round((file_size / duration) / (1000 * 1000), 2)

        if check_size:
            if expected_file_size != file_size:
                os.remove(file_path)
                print(f"Failed to download from {url}")
                return False

        print(
            f"Download of {file_name} successful. Average download speed: {speed} MB/s"
        )
        return file_path
                
    except Exception as e:
        print(e)
        print(f"Failed to download from {url}.")
        return False