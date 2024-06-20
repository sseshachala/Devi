import unittest
import os
import json
import sys
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

# Add the parent directory to the sys.path so we can import app and cloud_operations
sys.path.append('..')

from app import app
from cloud_operations import CloudOperations

class CloudOperationsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def add_auth_header(self):
        with open('.env.json') as config_file:
            config = json.load(config_file)
        api_key = config.get('API_KEY')
        return {'Authorization': api_key}

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_upload_to_cloud_success(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.upload_file = MagicMock()

        data = {
            'files': (open('tests/testfile.txt', 'rb'), 'testfile.txt')
        }

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.post('/uploadToCloud', content_type='multipart/form-data', data=data, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn('uploaded_files', json.loads(response.data))

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_upload_to_cloud_no_files(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.post('/uploadToCloud', headers=headers)

        self.assertEqual(response.status_code, 400)
        self.assertIn('No files part in the request', json.loads(response.data)['message'])

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_download_from_cloud_success(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.download_file = MagicMock()

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        with patch.object(instance.s3_resource.Object.return_value, 'download_file', return_value=None):
            response = self.app.get('/downloadFromCloud', query_string={'file_name': 'testfile.txt'}, headers=headers)

        self.assertEqual(response.status_code, 200)

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_download_from_cloud_no_file_name(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.get('/downloadFromCloud', headers=headers)

        self.assertEqual(response.status_code, 400)
        self.assertIn('No file_name provided', json.loads(response.data)['message'])

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_upload_to_cloud_fail(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.upload_file.side_effect = ClientError({'Error': {'Code': '500', 'Message': 'Upload failed'}}, 'Upload')

        data = {
            'files': (open('tests/testfile.txt', 'rb'), 'testfile.txt')
        }

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.post('/uploadToCloud', content_type='multipart/form-data', data=data, headers=headers)

        self.assertEqual(response.status_code, 500)
        self.assertIn('Upload failed', json.loads(response.data)['message'])

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_download_from_cloud_fail(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.download_file.side_effect = ClientError({'Error': {'Code': '404', 'Message': 'File testfile.txt not found in cloud'}}, 'Download')

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.get('/downloadFromCloud', query_string={'file_name': 'testfile.txt'}, headers=headers)

        self.assertEqual(response.status_code, 404)
        self.assertIn('File testfile.txt not found in cloud', json.loads(response.data)['message'])

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_list_files_success(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_bucket = mock_s3_resource.Bucket.return_value
        mock_bucket.objects.all.return_value = [
            MagicMock(key='file1.txt'),
            MagicMock(key='file2.jpg')
        ]

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.get('/listFiles', headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.data)['files']), 2)

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_view_file_success(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.download_file = MagicMock()

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        with patch.object(instance.s3_resource.Object.return_value, 'download_file', return_value=None):
            response = self.app.get('/viewFile', query_string={'file_name': 'testfile.txt'}, headers=headers)

        self.assertEqual(response.status_code, 200)

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_delete_file_success(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.delete = MagicMock()

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        headers = self.add_auth_header()
        response = self.app.delete('/deleteFile', query_string={'file_name': 'testfile.txt'}, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn('File testfile.txt deleted successfully', json.loads(response.data)['message'])

    @patch('cloud_operations.boto3.resource')
    @patch('cloud_operations.CloudOperations.__init__', lambda x: None)
    def test_delete_files_success(self, mock_boto_resource):
        mock_s3_resource = mock_boto_resource.return_value
        mock_s3_resource.Object.return_value.delete = MagicMock()

        # Manually set required instance attributes for testing
        instance = CloudOperations()
        instance.space_name = 'test_space'
        instance.region = 'test_region'
        instance.s3_resource = mock_s3_resource
        instance.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

        data = {
            'file_names': ['testfile1.txt', 'testfile2.txt']
        }

        headers = self.add_auth_header()
        response = self.app.delete('/deleteFiles', json=data, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Files [\'testfile1.txt\', \'testfile2.txt\'] deleted successfully', json.loads(response.data)['message'])

if __name__ == '__main__':
    # Create a temporary file to test file upload
    test_file_path = os.path.join('tests', 'testfile.txt')
    with open(test_file_path, 'w') as f:
        f.write('This is a test file.')

    try:
        unittest.main()
    finally:
        # Remove the temporary file after tests
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
