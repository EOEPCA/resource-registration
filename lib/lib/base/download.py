import os
import time
import netrc
import requests
from datetime import datetime


def access_token():
    """
    Description...

    Returns:
        (str): ...
    """
    if "token_expire_time" in os.environ and time.time() <= (float(os.environ["token_expire_time"]) - 5):
        return os.environ["s3_access_key"]

    print("Need to get a new access token")
    # todo: added try block & Exception raise for testing
    try:
        auth = netrc.netrc().authenticators("dataspace.copernicus.eu")
        username = auth[0]
        password = auth[2]
    except Exception as e:
        raise Exception("Failed to get credentials from netrc: %s" % e)
    auth_server_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    # response = requests.post(auth_server_url, data=data, verify=True, allow_redirects=False).json()
    # todo: added try block for testing
    try:
        response = requests.post(auth_server_url, data=data, verify=True, allow_redirects=False)
        response.raise_for_status()
        response_json = response.json()
    except requests.exceptions.RequestException as e:
        raise Exception("Failed to get access token: %s" % e)

    token_time = time.time()
    os.environ["token_expire_time"] = str(token_time + response_json["expires_in"])
    print(
        "New expiration tme for access token: %s"
        % datetime.fromtimestamp(float(os.environ["token_expire_time"])).strftime("%m/%d/%Y, %H:%M:%S")
    )
    os.environ["s3_access_key"] = response_json["access_token"]
    # () gelöscht
    return os.environ["s3_access_key"]


def download_data(
    url, output_dir, file_name=None, chunk_size=1024 * 1000, timeout=300, auth=None, check_size=True, overwrite=False
):
    """
    Download single file from USGS M2M by download url

    Parameters:
        url: x
        output_dir: x
        file_name: x
        chunk_size: x
        timeout: x
        auth: x
        check_size: x
        overwrite: x

    Returns:
        (str|bool): filepath or False
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
            except Exception:
                file_name = os.path.basename(url)
                # raise Exception("Can not automatically identify file_name.")

        print(f"Filename: {file_name}")
        file_path = os.path.join(output_dir, file_name)
        # TODO: Check for existing files and whether they have the correct file size
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if os.path.exists(file_path) and overwrite is False:
            return file_path
        elif os.path.exists(file_path) and overwrite is True:
            print("Removing old file")
            os.remove(file_path)

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

        print(f"Download of {file_name} successful. Average download speed: {speed} MB/s")
        return file_path

    except Exception as e:
        print(e)
        print(f"Failed to download from {url}.")
        return False
