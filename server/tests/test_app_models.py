from unittest import mock
from urllib.request import Request

import pytest
from dotenv import load_dotenv
import requests
import unittest
import pymongo
import os

from authentication import Token_Auth, User_Auth
from authentication.validate import User_Auth as mocked_user_auth
from authentication.errors import InvalidTokenError
from core.settings import DATABASE
from mainapp.errors import (
    FileAlreadyExistsForCurrentUserError,
    FileDoesNotExistForCurrentUserError,
)
from mainapp import (
    S3_Functions,
    Music_Data,
)
from . import Base
from authentication.validate import ValidateUser

from unittest.mock import patch, MagicMock


data = Base()


class TestAppModels(unittest.TestCase):
    """
    Integration tests
    """

    @classmethod
    def setUpClass(cls) -> None:

        load_dotenv()

        cls.client = requests.Session()
        cls.pymongo_client = pymongo.MongoClient(DATABASE["mongo_uri"])
        cls.m_db = cls.pymongo_client[DATABASE["db"]][os.getenv("DATA_COLLECTION")]
        cls.u_db = cls.pymongo_client[DATABASE["db"]][os.getenv("USER_DATA_COLLECTION")]
        cls.c_db = cls.pymongo_client[DATABASE["db"]][
            os.getenv("CONTACT_US_DATA_COLLECTION")
        ]
        cls.api_upload_url = "http://localhost:8000/api/app/uploads"
        cls.api_posts_url = "http://localhost:8000/api/app/posts"

    def test_file_exists(self):
        try:
            response = self.client.post(
                url=self.api_upload_url,
                data=data.test_data,
            )

            self.assertEqual(response.status_code, 200)

        except requests.exceptions.ConnectionError:
            print("Connection Error")

        # with self.assertRaises(FileAlreadyExistsForCurrentUserError):
        #     Music_Data.insert_data(
        #         data.test_data["Date"],
        #         data.test_data["Name"],
        #         data.test_data["Email"],
        #         data.test_data["Filename"],
        #         data.test_data["CloudFilename"],
        #         data.test_data["ObjectURL"],
        #     )

    def test_file_not_exists(self):
        with self.assertRaises(FileDoesNotExistForCurrentUserError):
            Music_Data.delete_data(
                data.wrong_data["wrong_email"], data.wrong_data["wrong_file"]
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.m_db.remove({})
        cls.u_db.remove({})
        cls.c_db.remove({})
        cls.pymongo_client.close()
        cls.client.close()
        try:
            S3_Functions.delete_file_from_s3(data.test_data["CloudFilename"])
        except Exception:
            print("Deletion Error")

    @patch.object(Token_Auth, 'decode_token')
    def test_user_validator_correct_behavior(self, token_auth):
        request = requests.get('http://random.com/test')
        request.headers = {"Authorization": "Bearer token"}
        token_auth.return_value = (True, {"id": "test_id", "role": "user"})
        with mock.patch.object(mocked_user_auth, "validate_uid", return_value=None):
            # User_Auth.validate_uid = MagicMock(return_value=None)
            validator = ValidateUser()
            assert validator.has_permission(request, None)

    def test_user_validator_token_exception(self):
        request = requests.get('http://random.com/test')
        request.headers = {"Authorization": "Bearer"}
        validator = ValidateUser()
        return_value = validator.has_permission(request, None)
        assert not return_value

    def test_user_validator_invalid_token(self):
        request = requests.get('http://random.com/test')
        request.headers = {"Authorization": "Bearer token"}
        validator = ValidateUser()
        return_value = validator.has_permission(request, None)
        assert not return_value

    @patch.object(Token_Auth, 'decode_token')
    def test_user_validator_second_exception(self, token_auth):
        request = requests.get('http://random.com/test')
        request.headers = {"Authorization": "Bearer token"}
        token_auth.return_value = ("test", True)
        validator = ValidateUser()
        return_value = validator.has_permission(request, None)
        assert not return_value

    @patch.object(Token_Auth, 'decode_token')
    def test_user_validator_invalid_user_UID(self, token_auth):
        request = requests.get('http://random.com/test')
        request.headers = {"Authorization": "Bearer token"}
        token_auth.return_value = (True, {"id": "test_id", "role": "user"})
        validator = ValidateUser()
        assert not validator.has_permission(request, None)

    @patch.object(Token_Auth, 'decode_token')
    def test_user_validator_third_exception(self, token_auth):
        request = requests.get('http://random.com/test')
        request.headers = {"Authorization": "Bearer token"}
        token_auth.return_value = (True, {"id": "id"})
        User_Auth.validate_uid = MagicMock(return_value=None)
        validator = ValidateUser()
        assert not validator.has_permission(request, None)


    def clean(self):
        self.m_db.remove({})
        self.u_db.remove({})
        self.c_db.remove({})
        try:
            S3_Functions.delete_file_from_s3(data.test_data["CloudFilename"])
        except Exception:
            print("Deletion Error")
