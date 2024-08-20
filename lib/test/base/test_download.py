import os
import time
from unittest import mock
import pytest

import requests
from lib.base.download import access_token


# Test if the function returns the existing token if it is not expired
def test_access_token_existing_valid_token(monkeypatch):
    # Set up the environment with a valid token and expiry time
    monkeypatch.setenv("token_expire_time", str(time.time() + 3600))  # Token valid for the next hour
    monkeypatch.setenv("s3_access_key", "existing_valid_token")

    assert access_token() == "existing_valid_token"


# Test if the function requests a new token if the existing one is expired
def test_access_token_expired_token_with_mock(monkeypatch):
    # Set up environment variables
    monkeypatch.setenv("token_expire_time", str(time.time() - 3600))  # Token expired
    monkeypatch.setenv("s3_access_key", "expired_token")

    # Verify that the current token is indeed the expired token
    assert os.environ.get("s3_access_key") == "expired_token"

    # Mock the netrc file
    with mock.patch("netrc.netrc") as mock_netrc:
        mock_auth = ("username", None, "password")  # Mock username and password
        mock_netrc.return_value.authenticators.return_value = mock_auth

        # Mock the requests.post method
        with mock.patch("requests.post") as mock_post:
            # Simulate a successful token response
            mock_response = mock.MagicMock()
            mock_response.json.return_value = {"access_token": "new_token", "expires_in": 3600}
            mock_post.return_value = mock_response

            new_token = access_token()

            assert new_token == "new_token"
            assert os.environ["s3_access_key"] == "new_token"
            assert float(os.environ["token_expire_time"]) > time.time()


# Test if the function correctly requests a new token when no token is set
def test_access_token_no_existing_token(monkeypatch):
    # Mock the netrc file
    with mock.patch("netrc.netrc") as mock_netrc:
        mock_auth = ("username", None, "password")  # Mock username and password
        mock_netrc.return_value.authenticators.return_value = mock_auth

        # Mock the requests.post method
        with mock.patch("requests.post") as mock_post:
            # Simulate a successful token response
            mock_response = mock.MagicMock()
            mock_response.json.return_value = {"access_token": "new_token", "expires_in": 3600}
            mock_post.return_value = mock_response

            # Remove environment variables
            monkeypatch.delenv("token_expire_time", raising=False)
            monkeypatch.delenv("s3_access_key", raising=False)

            new_token = access_token()
            assert new_token == "new_token"
            assert os.environ["s3_access_key"] == "new_token"
            assert float(os.environ["token_expire_time"]) > time.time()


# Test if the function handles network errors gracefully
def test_access_token_network_error(monkeypatch):
    # Mock the netrc file
    with mock.patch("netrc.netrc") as mock_netrc:
        mock_auth = ("username", None, "password")  # Mock username and password
        mock_netrc.return_value.authenticators.return_value = mock_auth

        monkeypatch.setenv("token_expire_time", str(time.time() - 3600))  # Token expired

        with mock.patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Network error")

            with pytest.raises(Exception, match="Failed to get access token"):
                access_token()


# Test if the function handles missing credentials in the netrc file gracefully
def test_access_token_missing_credentials(monkeypatch):
    with mock.patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"access_token": "new_token", "expires_in": 3600}

        with mock.patch("netrc.netrc") as mock_netrc:
            mock_netrc.return_value.authenticators.side_effect = Exception("Netrc error")

            monkeypatch.setenv("token_expire_time", str(time.time() - 3600))  # Token expired

            with pytest.raises(Exception, match="Failed to get credentials from netrc"):
                access_token()


# Test if the function handles an invalid response from the token server gracefully
def test_access_token_invalid_response():
    # Mock the netrc file
    with mock.patch("netrc.netrc") as mock_netrc:
        mock_auth = ("username", None, "password")  # Mock username and password
        mock_netrc.return_value.authenticators.return_value = mock_auth

        with mock.patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"unexpected_key": "value"}

            with mock.patch.dict(os.environ, {"token_expire_time": str(time.time() - 3600)}):
                with pytest.raises(KeyError):
                    access_token()
