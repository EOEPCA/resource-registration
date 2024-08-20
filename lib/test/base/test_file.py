import io
import os
import shutil
import tarfile
import tempfile
from unittest import mock

import pytest
import zipfile
from lib.base.file import (
    zip_directory,
    delete_file,
    unzip_file,
    calculate_checksum,
    get_folder_size,
    untar_file,
    check_file_size,
    get_file_size,
)


# @pytest.fixture(autouse=True)
# def temp_directory():
#     # Create a temporary directory for testing
#     temp_dir = tempfile.mkdtemp()
#     yield temp_dir
#
#     # Clean up the temporary directory after the test
#     for filename in os.listdir(temp_dir):
#         file_path = os.path.join(temp_dir, filename)
#         # Check if the path points to a file (not a directory)
#         if os.path.isfile(file_path):
#             # Delete the file
#             os.remove(file_path)
#     os.rmdir(temp_dir)


def cleanup_directory(directory):
    shutil.rmtree(directory)  # Löscht rekursiv das Verzeichnis und alle Inhalte


@pytest.fixture(autouse=True)
def temp_directory():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    cleanup_directory(temp_dir)


@pytest.fixture
def zip_file_path(temp_directory):
    zip_file_path = os.path.join(temp_directory, "test.zip")
    with zipfile.ZipFile(zip_file_path, "w") as zipf:
        zipf.writestr("folder/test.txt", "Test content")
    return zip_file_path


@pytest.fixture
def create_test_tar(temp_directory):
    tar_file = os.path.join(temp_directory, "test.tar")
    temp_file = os.path.join(temp_directory, "test.txt")

    with tarfile.open(tar_file, "w") as tar:
        with open(temp_file, "w") as f:
            f.write("Test content")
        tar.add(temp_file, arcname="test.txt")

    return tar_file


def test_zip_directory(temp_directory):
    # Create a test file inside the temporary directory
    test_file = os.path.join(temp_directory, "test.txt")
    with open(test_file, "w") as f:
        f.write("This is a test file.")

    # Zip the temporary directory
    zip_file_path = zip_directory(temp_directory)

    # Check if the zip file is created
    assert os.path.isfile(zip_file_path)

    # Check if the zip file name matches the directory name
    assert os.path.basename(zip_file_path) == os.path.basename(temp_directory) + ".zip"

    # Check if the zip file contains the test file
    with zipfile.ZipFile(zip_file_path, "r") as zipf:
        assert "test.txt" in zipf.namelist()


def test_zip_directory_invalid_source():
    # Test invalid source path
    with pytest.raises(ValueError):
        zip_directory("/invalid/path")


def test_zip_directory_existing_destination(temp_directory):
    # Create a test file inside the temporary directory
    test_file = os.path.join(temp_directory, "test.txt")
    with open(test_file, "w") as f:
        f.write("This is a test file.")

    # Create a test zip file in the temporary directory
    test_zip_path = os.path.join(temp_directory, "test.zip")
    with zipfile.ZipFile(test_zip_path, "w") as zipf:
        zipf.write(os.path.join(temp_directory, "test.txt"), "test.txt")

    # Test destination path already exists
    with pytest.raises(ValueError):
        zip_directory(temp_directory, test_zip_path)


def test_delete_file():
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test_iif.xml")
    with open(test_file, "w") as f:
        f.write("<IIF></IIF>")

    delete_file(test_file)
    assert not os.path.isfile(test_file)
    os.rmdir(temp_dir)


def test_delete_file_not_existing():
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test_iif.xml")
    with pytest.raises(Exception):
        delete_file(test_file)
    os.rmdir(temp_dir)


def test_delete_file_is_dir():
    temp_dir = tempfile.mkdtemp()
    with pytest.raises(Exception):
        delete_file(temp_dir)
    os.rmdir(temp_dir)


# Test if the function raises an exception when the ZIP file does not exist
def test_unzip_file_not_existing():
    with pytest.raises(Exception, match="File does not exist"):
        unzip_file("non_existing_file.zip")


# Test if the function correctly unzips a valid ZIP file and returns the correct path and removal status
def test_unzip_file_success(zip_file_path):
    result = unzip_file(zip_file_path)
    assert os.path.exists(result["scene_path"])
    assert os.path.isfile(os.path.join(result["scene_path"], "test.txt"))
    assert result["zip_file_removed"] is True


# Test if the function handles errors during file extraction properly
def test_unzip_file_with_failed_files(zip_file_path):
    # Simuliere einen Fehler beim Entpacken
    with mock.patch.object(zipfile.ZipFile, "extract", side_effect=Exception("Extraction failed")):
        with pytest.raises(Exception, match="Exceptions during unzipping"):
            unzip_file(zip_file_path)


# Test if the function removes the ZIP file when 'remove_zip=True'
def test_unzip_file_remove_zip(zip_file_path):
    result = unzip_file(zip_file_path, remove_zip=True)
    assert result["zip_file_removed"] is True
    assert not os.path.exists(zip_file_path)


# Test if the function does not remove the ZIP file when 'remove_zip=False'
def test_unzip_file_keep_zip(zip_file_path):
    result = unzip_file(zip_file_path, remove_zip=False)
    assert result["zip_file_removed"] is False
    assert os.path.exists(zip_file_path)


# Test if the function handles ZIP files without subfolders correctly
def test_unzip_file_no_subfolder(temp_directory):
    zip_file_path = os.path.join(temp_directory, "test.zip")
    with zipfile.ZipFile(zip_file_path, "w") as zipf:
        zipf.writestr("test.txt", "Test content")

    with pytest.raises(Exception, match="Could not find sub-folder in zip file"):
        unzip_file(zip_file_path)


# Test if the function raises an exception for invalid or corrupted ZIP files
def test_unzip_file_invalid_zip(temp_directory):
    invalid_zip_file = os.path.join(temp_directory, "invalid.zip")
    with open(invalid_zip_file, "w") as f:
        f.write("This is not a valid zip file")

    with pytest.raises(zipfile.BadZipFile):
        unzip_file(invalid_zip_file)


# Test if the function raises an exception for an unsupported checksum algorithm
def test_calculate_checksum_unsupported_algorithm():
    # Test with an unsupported algorithm name
    with pytest.raises(Exception, match="Checksum algorithm not available"):
        calculate_checksum("unsupported_algorithm", "file.txt")

    # Test with an empty algorithm name
    with pytest.raises(Exception, match="Checksum algorithm not available"):
        calculate_checksum("", "file.txt")


# Test if the function calculates the checksum correctly using a supported algorithm
def test_calculate_checksum_correct_algorithm(temp_directory):
    test_file = os.path.join(temp_directory, "test.txt")
    with open(test_file, "w") as f:
        f.write("Test")

    # Expected checksum value (e.g., MD5 hash)
    expected_checksum = "0cbc6611f5540bd0809a388dc95a615b"  # Example value for "Test" with MD5
    result = calculate_checksum("MD5", test_file)
    assert result == expected_checksum


# Test if the function handles missing files correctly
def test_calculate_checksum_file_not_found():
    with pytest.raises(FileNotFoundError):
        calculate_checksum("MD5", "non_existing_file.txt")


# Test if the function handles empty files correctly
def test_calculate_checksum_empty_file(temp_directory):
    empty_file = os.path.join(temp_directory, "empty.txt")
    open(empty_file, "w").close()

    # Expected checksum value for an empty file (e.g., MD5 hash of an empty string)
    expected_checksum = "d41d8cd98f00b204e9800998ecf8427e"  # Example value for an empty file with MD5
    result = calculate_checksum("MD5", empty_file)
    assert result == expected_checksum


# Test if the function handles binary files correctly
def test_calculate_checksum_binary_file(temp_directory):
    binary_file = os.path.join(temp_directory, "binary.bin")
    with open(binary_file, "wb") as f:
        f.write(b"\x00\x01\x02\x03")

    # Expected checksum value for the binary content
    expected_checksum = "37b59afd592725f9305e484a5d7f5168"  # Example value for binary content with MD5
    result = calculate_checksum("MD5", binary_file)
    assert result == expected_checksum


# Test if the function raises an exception for a non-existent folder
def test_get_folder_size_folder_not_exist():
    with pytest.raises(Exception, match="Folder .* does not exist!"):
        get_folder_size("non_existing_folder")


# Test if the function returns 0 for an empty folder
def test_get_folder_size_empty_folder(temp_directory):
    empty_folder = os.path.join(temp_directory, "empty")
    os.makedirs(empty_folder)
    size = get_folder_size(empty_folder)
    assert size == 0


# Test if the function calculates the size correctly for a folder with a single file
def test_get_folder_size_single_file(temp_directory):
    single_file_folder = os.path.join(temp_directory, "single_file")
    os.makedirs(single_file_folder)
    file_path = os.path.join(single_file_folder, "file.txt")
    with open(file_path, "w") as f:
        f.write("Test content")
    size = get_folder_size(single_file_folder)
    assert size == os.path.getsize(file_path)


# Test if the function calculates the total size correctly for a folder with multiple files
def test_get_folder_size_multiple_files(temp_directory):
    multiple_files_folder = os.path.join(temp_directory, "multiple_files")
    os.makedirs(multiple_files_folder)
    file_paths = [os.path.join(multiple_files_folder, "file1.txt"), os.path.join(multiple_files_folder, "file2.txt")]
    with open(file_paths[0], "w") as f:
        f.write("Content 1")
    with open(file_paths[1], "w") as f:
        f.write("Content 2")
    total_size = sum(os.path.getsize(fp) for fp in file_paths)
    size = get_folder_size(multiple_files_folder)
    assert size == total_size


# Test if the function calculates the size correctly for a folder with subfolders
def test_get_folder_size_with_subfolders(temp_directory):
    main_folder = os.path.join(temp_directory, "main_folder")
    os.makedirs(main_folder)
    subfolder = os.path.join(main_folder, "subfolder")
    os.makedirs(subfolder)

    file_in_main = os.path.join(main_folder, "main_file.txt")
    file_in_sub = os.path.join(subfolder, "sub_file.txt")

    with open(file_in_main, "w") as f:
        f.write("Main file content")
    with open(file_in_sub, "w") as f:
        f.write("Subfolder file content")

    total_size = os.path.getsize(file_in_main) + os.path.getsize(file_in_sub)
    size = get_folder_size(main_folder)
    assert size == total_size


# Test if the function raises an exception when the TAR file does not exist
def test_untar_file_file_not_exist():
    with pytest.raises(Exception, match="File does not exist: .*"):
        untar_file("non_existing_file.tar")


# Test if the function successfully extracts a valid TAR file
def test_untar_file_successful_extraction(temp_directory, create_test_tar):
    tar_file = create_test_tar
    extract_dir = os.path.join(temp_directory, "extracted")

    result = untar_file(tar_file, base_folder=extract_dir)

    assert os.path.isfile(os.path.join(result["scene_path"], "test.txt"))
    assert result["zip_file_removed"] is True
    assert result["scene_path"] == extract_dir


# Test if the function removes the TAR file after extraction when remove_tar=True
def test_untar_file_remove_tar_after_extraction(temp_directory, create_test_tar):
    tar_file = create_test_tar

    result = untar_file(tar_file, remove_tar=True, create_folder=True, base_folder=temp_directory)

    assert not os.path.exists(tar_file)
    assert result["zip_file_removed"] is True


# Test if the function creates a new folder for the extracted files when create_folder=True
def test_untar_file_create_folder(temp_directory, create_test_tar):
    tar_file = create_test_tar

    result = untar_file(tar_file, remove_tar=False, create_folder=True, base_folder=temp_directory)

    expected_folder = os.path.join(temp_directory, "test")
    assert os.path.exists(expected_folder)
    assert result["scene_path"] == expected_folder


# Test if the function extracts files to a custom base folder when base_folder is provided
def test_untar_file_custom_base_folder(temp_directory, create_test_tar):
    tar_file = create_test_tar
    custom_folder = os.path.join(temp_directory, "custom_folder")
    os.makedirs(custom_folder)

    result = untar_file(tar_file, create_folder=False, base_folder=custom_folder)

    extracted_file = os.path.join(custom_folder, "test.txt")
    assert os.path.exists(extracted_file)
    assert result["scene_path"] == custom_folder


# Test if the function handles extraction failures correctly and logs failed files
def test_untar_file_failed_extraction(temp_directory):
    tar_file = os.path.join(temp_directory, "test.tar")

    # Create a TAR file with invalid file paths
    with tarfile.open(tar_file, "w") as tar:
        tarinfo = tarfile.TarInfo("invalid/../test.txt")
        tarinfo.size = len(b"Invalid content")
        tar.addfile(tarinfo, io.BytesIO(b"Invalid content"))

    # Patch tarfile.extract to raise an exception
    with mock.patch.object(tarfile.TarFile, "extract", side_effect=Exception("Mocked extraction failure")):
        with pytest.raises(Exception, match="Exceptions during untaring: .*"):
            untar_file(tar_file, remove_tar=False, base_folder=temp_directory)


# Test if the function raises an exception when given a file that is not a valid TAR file
def test_untar_file_invalid_tar(temp_directory):
    not_a_tar_file = os.path.join(temp_directory, "not_a_tar.txt")

    with open(not_a_tar_file, "w") as f:
        f.write("This is not a TAR file.")

    with pytest.raises(tarfile.ReadError):
        untar_file(not_a_tar_file, remove_tar=False, base_folder=temp_directory)


def test_untar_file_tar_not_removed_on_delete_error(temp_directory, create_test_tar):
    tar_file = create_test_tar

    with mock.patch("os.remove", side_effect=PermissionError("Mocked permission error")):
        result = untar_file(tar_file, remove_tar=True, create_folder=False, base_folder=temp_directory)

        assert os.path.exists(tar_file)
        assert result["zip_file_removed"] is False


# Test if the function correctly identifies when the file size matches the expected size
def test_check_file_size_success(temp_directory):
    test_file = os.path.join(temp_directory, "test_file.txt")
    with open(test_file, "w") as f:
        f.write("Test")

    assert check_file_size(4, test_file) is True


# Test if the function raises an exception when the file does not exist
def test_check_file_size_file_not_found(temp_directory):
    non_existent_file = os.path.join(temp_directory, "non_existent_file.txt")

    with pytest.raises(Exception, match="File not found: "):
        check_file_size(0, non_existent_file)


# Test if the function returns the correct size for an existing file
def test_get_file_size_existing_file(temp_directory):
    test_file = os.path.join(temp_directory, "test_file.txt")
    with open(test_file, "w") as f:
        f.write("Sample content")

    assert get_file_size(test_file) == len("Sample content")


# Test if the function raises an exception when the file does not exist
def test_get_file_size_file_not_found(temp_directory):
    non_existent_file = os.path.join(temp_directory, "non_existent_file.txt")

    with pytest.raises(Exception, match="File .* does not exist!"):
        get_file_size(non_existent_file)
