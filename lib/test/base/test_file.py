import os
import tempfile
import pytest
import zipfile
from terrabyte.ingestion.base.file import zip_directory, delete_file

@pytest.fixture(autouse=True)
def temp_directory():
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    # Clean up the temporary directory after the test
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        # Check if the path points to a file (not a directory)
        if os.path.isfile(file_path):
            # Delete the file
            os.remove(file_path)
    os.rmdir(temp_dir)

def test_zip_directory(temp_directory):
    # Create a test file inside the temporary directory
    test_file = os.path.join(temp_directory, "test.txt")
    with open(test_file, 'w') as f:
        f.write("This is a test file.")

    # Zip the temporary directory
    zip_file_path = zip_directory(temp_directory)

    # Check if the zip file is created
    assert os.path.isfile(zip_file_path)

    # Check if the zip file name matches the directory name
    assert os.path.basename(zip_file_path) == os.path.basename(temp_directory) + ".zip"

    # Check if the zip file contains the test file
    with zipfile.ZipFile(zip_file_path, 'r') as zipf:
        assert "test.txt" in zipf.namelist()

def test_zip_directory_invalid_source():
    # Test invalid source path
    with pytest.raises(ValueError):
        zip_directory("/invalid/path")

def test_zip_directory_existing_destination(temp_directory):
    # Create a test file inside the temporary directory
    test_file = os.path.join(temp_directory, "test.txt")
    with open(test_file, 'w') as f:
        f.write("This is a test file.")

    # Create a test zip file in the temporary directory
    test_zip_path = os.path.join(temp_directory, "test.zip")
    with zipfile.ZipFile(test_zip_path, 'w') as zipf:
        zipf.write(os.path.join(temp_directory, "test.txt"), "test.txt")

    # Test destination path already exists
    with pytest.raises(ValueError):
        zip_directory(temp_directory, test_zip_path)

def test_delete_file():
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test_iif.xml")
    with open(test_file, 'w') as f:
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
