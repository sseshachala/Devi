import os
import json
import logging
from flask import Flask, request, jsonify, send_file
from flask_restx import Api, Resource, fields
from functools import wraps
from cloud_operations import CloudOperations

app = Flask(__name__)
api = Api(app, version='1.0', title='Cloud Operations API',
          description='A simple API to interact with cloud storage',
          )

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
with open('.env.json') as config_file:
    config = json.load(config_file)

API_KEY = config.get('API_KEY')

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            return jsonify({'status': 'fail', 'message': 'API key is missing'}), 401
        api_key = request.headers['Authorization']
        if api_key != API_KEY:
            return jsonify({'status': 'fail', 'message': 'Invalid API key'}), 403
        return f(*args, **kwargs)
    return decorated_function

cloud_ops = CloudOperations()

upload_model = api.model('UploadModel', {
    'files': fields.List(fields.Raw, required=True, description='List of files to be uploaded')
})

delete_files_model = api.model('DeleteFilesModel', {
    'file_names': fields.List(fields.String, required=True, description='List of file names to be deleted')
})

@api.route('/uploadToCloud')
class UploadToCloud(Resource):
    @api.expect(upload_model)
    @require_api_key
    def post(self):
        response, status = cloud_ops.upload_to_cloud(request)
        return jsonify(response), status

@api.route('/downloadFromCloud')
class DownloadFromCloud(Resource):
    @require_api_key
    def get(self):
        response, status = cloud_ops.download_from_cloud(request)
        return jsonify(response), status

@api.route('/listFiles')
class ListFiles(Resource):
    @require_api_key
    def get(self):
        response, status = cloud_ops.list_files()
        return jsonify(response), status

@api.route('/viewFile')
class ViewFile(Resource):
    @require_api_key
    def get(self):
        response, status = cloud_ops.view_file(request)
        return send_file(response), status

@api.route('/deleteFile')
class DeleteFile(Resource):
    @require_api_key
    def delete(self):
        response, status = cloud_ops.delete_file(request)
        return jsonify(response), status

@api.route('/deleteFiles')
class DeleteFiles(Resource):
    @api.expect(delete_files_model)
    @require_api_key
    def delete(self):
        response, status = cloud_ops.delete_files(request)
        return jsonify(response), status

if __name__ == '__main__':
    app.run(debug=True)
