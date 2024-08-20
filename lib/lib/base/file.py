import os
import zipfile
import tarfile
import hashlib

# todo: module-attributes in docs?
checksum_funcs = dict()
checksum_funcs["SHA3-256"] = hashlib.sha3_256
checksum_funcs["MD5"] = hashlib.md5

try:
    import blake3

    checksum_funcs["BLAKE3"] = blake3.blake3
except Exception:
    pass


def zip_directory(source_path, destination_path=None):
    """
    Compress the contents of a directory into a zip file.

    Args:
        source_path (str): The path to the source directory to be compressed.
        destination_path (str, optional): The path where the zip file will be created.
            If not provided, the zip file will be created in the same directory as the source directory
            with the name of the source directory plus .zip extension. Defaults to None.

    Returns:
        (str): The path to the generated zip file.

    Raises:
        ValueError: If the source_path is not a directory or if the destination_path already exists.
    """
    if not os.path.isdir(source_path):
        raise ValueError("Source path is not a directory.")

    if destination_path is None:
        destination_path = os.path.join(os.path.dirname(source_path), os.path.basename(source_path) + ".zip")

    if os.path.exists(destination_path):
        raise ValueError("Destination path already exists.")

    with zipfile.ZipFile(destination_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, source_path)
                zipf.write(file_path, relative_path)

    return destination_path


def unzip_file(zip_file, remove_zip=True, extract_dir=None):
    """
    Unzips a Sentinel scene and lists failed files

    Arguments:
        zip_file: zip file to unzip
        remove_zip: Whether zip file is being removed or not (default: True)
        extract_dir: x

    Returns:
        (dict): scene_path with folder of unzipped file and boolean zip_file_removed
    """
    if not os.path.exists(zip_file):
        raise Exception("File does not exist: %s" % zip_file)

    if extract_dir is None:
        extract_dir = os.path.dirname(zip_file)

    failed_files = dict()
    failed_logs = ""

    with zipfile.ZipFile(zip_file, "r") as zip_ref:  # with block added bc os.remove raised WinErr32
        for name in zip_ref.namelist():
            try:
                zip_ref.extract(name, extract_dir)
            except Exception as e:
                failed_files[name] = str(e)
                failed_logs += name + ": " + str(e) + "\n"

        if len(failed_files) > 0:
            raise Exception("Exceptions during unzipping: %s\n\n%s" % (zip_file, failed_logs))
        else:  # removed try block bc sub-folder error wasn't caught
            zip_folder_list = zip_ref.namelist()[0].split("/")
            if len(zip_folder_list) < 2:
                raise Exception("Could not find sub-folder in zip file %s" % zip_file)
            zip_folder = zip_folder_list[0]

            response_dict = {"scene_path": os.path.join(extract_dir, zip_folder)}

    if remove_zip:
        try:
            os.remove(zip_file)
            response_dict["zip_file_removed"] = True
        except Exception:
            response_dict["zip_file_removed"] = False
    else:
        response_dict["zip_file_removed"] = False
    return response_dict


def untar_file(tar_file, remove_tar=True, create_folder=False, base_folder=None):
    """
    Untars a scene and lists failed files

    Arguments:
        tar_file: tar file to untar
        remove_tar: Whether tar file is being removed or not (default: True)
        create_folder: x
        base_folder: x

    Returns:
        (dict): scene_path with folder of untared file
    """
    if not os.path.exists(tar_file):
        raise Exception("File does not exist: %s" % tar_file)

    tar_ref = tarfile.open(tar_file, "r:")
    if not base_folder:
        base_folder = os.path.dirname(tar_file)
    if create_folder:
        scene_name = os.path.splitext(os.path.basename(tar_file))[0]
        extract_dir = os.path.join(base_folder, scene_name)
    else:
        extract_dir = base_folder

    failed_files = dict()
    failed_logs = ""

    for name in tar_ref.getnames():
        try:
            tar_ref.extract(name, extract_dir)
        except Exception as e:
            failed_files[name] = str(e)
            failed_logs += name + ": " + str(e) + "\n"

    tar_ref.close()

    if len(failed_files) > 0:
        raise Exception("Exceptions during untaring: %s\n\n%s" % (tar_file, failed_logs))
    else:
        response_dict = {"scene_path": extract_dir}
        if remove_tar:
            try:
                os.remove(tar_file)
                response_dict["zip_file_removed"] = True
                print("Tar-File successfully removed: %s" % tar_file)
            except Exception as e:
                response_dict["zip_file_removed"] = False
                print(e)
                print("Tar-File could not be removed: %s" % tar_file)
        return response_dict


def check_file_size(expected_file_size, file_path):
    """
    Description...

    Parameters:
        expected_file_size: x
        file_path: x

    Returns:
        (bool): ...

    Raises:
        Exception: File not found.
    """
    if os.path.isfile(file_path):
        actual_file_size = os.path.getsize(file_path)
        if expected_file_size == actual_file_size:
            return True
        else:
            print(f"Different file sizes - {expected_file_size} expected - {actual_file_size} found")
            return False
    else:
        raise Exception("File not found: {file_path}")


def get_file_size(file_path):
    """
    Description...

    Parameters:
        file_path: x

    Returns:
        (...): ...

    Raises:
        Exception: File does not exist.
    """
    if not os.path.exists(file_path):
        raise Exception("File %s does not exist!" % file_path)
    stat = os.stat(file_path)
    return stat.st_size


def get_folder_size(folder_path):
    """
    Description...

    Parameters:
        folder_path: x

    Returns:
        (...): ...

    Raises:
        Exception: Folder does not exist.
    """
    if not os.path.exists(folder_path):
        raise Exception("Folder %s does not exist!" % folder_path)
    size = 0
    for path, dirs, files in os.walk(folder_path):
        for f in files:
            fp = os.path.join(path, f)
            stat = os.stat(fp)
            size += stat.st_size
    return size


def calculate_checksum(algorithm, check_file):
    """
    Description...

    Parameters:
        algorithm: x
        check_file: x

    Returns:
        (...): ...

    Raises:
        Exception: Checksum algorithm not available.
    """
    if algorithm not in checksum_funcs:
        raise Exception("Checksum algorithm not available")
    checksum = checksum_funcs[algorithm](open(check_file, "rb").read()).hexdigest().lower()
    return checksum


def delete_file(file: str):
    """
    Description...

    Parameters:
        algorithm: x
        check_file: x

    Returns:
        (...): ...

    Raises:
        OSError: ...
    """
    try:
        os.remove(file)
    except OSError as e:
        raise Exception("Error: %s - %s." % (e.filename, e.strerror))
