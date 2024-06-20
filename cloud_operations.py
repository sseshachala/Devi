import os
import json
import logging
import threading
import mimetypes
import sys
from flask import jsonify, send_file
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import NoCredentialsError, ClientError


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()

class CloudOperations:
    def __init__(self):
        # Read configuration from .env.json
        with open('.env.json') as config_file:
            config = json.load(config_file)

        logger.info('Loaded configuration from .env.json')

        self.space_name = config.get('AWS_BUCKET_NAME')
        self.region = config.get('AWS_DEFAULT_REGION')
        
        self.s3_resource = boto3.resource(
            's3',
            region_name=self.region,
            aws_access_key_id=config.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=config.get('AWS_SECRET_ACCESS_KEY')
        )

        self.config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )

    def upload_to_cloud(self, request):
        try:
            if 'files' not in request.files:
                logger.error('No files part in the request')
                return {'status': 'fail', 'message': 'No files part in the request'}, 400

            files = request.files.getlist('files')
            uploaded_files = []

            for file in files:
                file_name = file.filename
                file.save(file_name)

                try:
                    mime_type, _ = mimetypes.guess_type(file_name)
                    self.s3_resource.Object(self.space_name, file_name).upload_file(
                        file_name,
                        ExtraArgs={'ContentType': mime_type},
                        Config=self.config,
                        Callback=ProgressPercentage(file_name)
                    )
                    uploaded_files.append(file_name)
                    os.remove(file_name)
                    logger.info(f'Uploaded file {file_name} to cloud')
                except FileNotFoundError:
                    logger.error(f'File {file_name} not found')
                    return {'status': 'fail', 'message': f'File {file_name} not found'}, 404
                except NoCredentialsError:
                    logger.error('Credentials not available')
                    return {'status': 'fail', 'message': 'Credentials not available'}, 403
                except ClientError as e:
                    logger.error(f'Client error: {str(e)}')
                    return {'status': 'fail', 'message': str(e)}, 500

            return {'status': 'success', 'uploaded_files': uploaded_files}, 200

        except Exception as e:
            logger.error(f'Exception: {str(e)}')
            return {'status': 'fail', 'message': str(e)}, 500

    def download_from_cloud(self, request):
        try:
            file_name = request.args.get('file_name')
            if not file_name:
                logger.error('No file_name provided')
                return {'status': 'fail', 'message': 'No file_name provided'}, 400

            local_file_path = os.path.join('/tmp', file_name)

            try:
                self.s3_resource.Object(self.space_name, file_name).download_file(
                    local_file_path,
                    Config=self.config,
                    Callback=ProgressPercentage(local_file_path)
                )
                logger.info(f'Downloaded file {file_name} from cloud')
                return send_file(local_file_path), 200
            except FileNotFoundError:
                logger.error(f'File {file_name} not found in cloud')
                return {'status': 'fail', 'message': f'File {file_name} not found in cloud'}, 404
            except NoCredentialsError:
                logger.error('Credentials not available')
                return {'status': 'fail', 'message': 'Credentials not available'}, 403
            except ClientError as e:
                logger.error(f'Client error: {str(e)}')
                return {'status': 'fail', 'message': str(e)}, 500

        except Exception as e:
            logger.error(f'Exception: {str(e)}')
            return {'status': 'fail', 'message': str(e)}, 500

    def list_files(self):
        try:
            bucket = self.s3_resource.Bucket(self.space_name)
            files = []
            for obj in bucket.objects.all():
                mime_type, _ = mimetypes.guess_type(obj.key)
                files.append({'file_name': obj.key, 'mime_type': mime_type})
            return {'status': 'success', 'files': files}, 200
        except ClientError as e:
            logger.error(f'Client error: {str(e)}')
            return {'status': 'fail', 'message': str(e)}, 500

    def view_file(self, request):
        try:
            file_name = request.args.get('file_name')
            if not file_name:
                logger.error('No file_name provided')
                return {'status': 'fail', 'message': 'No file_name provided'}, 400

            local_file_path = os.path.join('/tmp', file_name)

            try:
                self.s3_resource.Object(self.space_name, file_name).download_file(
                    local_file_path,
                    Config=self.config,
                    Callback=ProgressPercentage(local_file_path)
                )
                mime_type, _ = mimetypes.guess_type(local_file_path)
                logger.info(f'Viewing file {file_name} from cloud')
                return send_file(local_file_path, mimetype=mime_type), 200
            except FileNotFoundError:
                logger.error(f'File {file_name} not found in cloud')
                return {'status': 'fail', 'message': f'File {file_name} not found in cloud'}, 404
            except NoCredentialsError:
                logger.error('Credentials not available')
                return {'status': 'fail', 'message': 'Credentials not available'}, 403
            except ClientError as e:
                logger.error(f'Client error: {str(e)}')
                return {'status': 'fail', 'message': str(e)}, 500

        except Exception as e:
            logger.error(f'Exception: {str(e)}')
            return {'status': 'fail', 'message': str(e)}, 500

    def delete_file(self, request):
        try:
            file_name = request.args.get('file_name')
            if not file_name:
                logger.error('No file_name provided')
                return {'status': 'fail', 'message': 'No file_name provided'}, 400

            try:
                self.s3_resource.Object(self.space_name, file_name).delete()
                logger.info(f'Deleted file {file_name} from cloud')
                return {'status': 'success', 'message': f'File {file_name} deleted successfully'}, 200
            except ClientError as e:
                logger.error(f'Client error: {str(e)}')
                return {'status': 'fail', 'message': str(e)}, 500

        except Exception as e:
            logger.error(f'Exception: {str(e)}')
            return {'status': 'fail', 'message': str(e)}, 500

    def delete_files(self, request):
        try:
            file_names = request.json.get('file_names')
            if not file_names:
                logger.error('No file_names provided')
                return {'status': 'fail', 'message': 'No file_names provided'}, 400

            try:
                for file_name in file_names:
                    self.s3_resource.Object(self.space_name, file_name).delete()
                logger.info(f'Deleted files {file_names} from cloud')
                return {'status': 'success', 'message': f'Files {file_names} deleted successfully'}, 200
            except ClientError as e:
                logger.error(f'Client error: {str(e)}')
                return {'status': 'fail', 'message': str(e)}, 500

        except Exception as e:
            logger.error(f'Exception: {str(e)}')
            return {'status': 'fail', 'message': str(e)}, 500
        
    def process_file(self, request):
