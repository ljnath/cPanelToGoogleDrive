"""
MIT License

Copyright (c) 2024-2025 Lakhya Jyoti Nath (ljnath)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

cPanelBackupPlus - Automated cPanel Full Backup to AmazonS3, Google Drive and more
Version: 1.1
Author: Lakhya Jyoti Nath (ljnath)
Email:  ljnath@ljnath.com
Website: https://ljnath.com

"""
import mimetypes
from abc import ABC, abstractmethod
import argparse
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import re
import requests
import boto3
import os
import time
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


"""
LOADING USER CONFIG FROM .ENV file
"""
load_dotenv()

CPANEL_URL = os.getenv("CPANEL_URL")
CPANEL_USERNAME = os.getenv("CPANEL_USERNAME")
CPANEL_API_TOKEN = os.getenv("CPANEL_API_TOKEN")

AWS_PROFILE = os.getenv("AWS_PROFILE_NAME")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_BACKUP_KEY_PREFIX = os.getenv("S3_BACKUP_KEY_PREFIX")

MAX_BACKUP_FILES = int(os.getenv("MAX_BACKUP_FILES"))
BACKUP_CHECK_DELAY = int(os.getenv("BACKUP_CHECK_DELAY"))
BACKUP_DESTINATION_EMAIL = os.getenv("BACKUP_EMAIL")

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

APP_NAME = 'cPanelBackupPlus'
APP_VERSION = '1.0'
LOGS_DIRECTORY = 'logs'


class LogHandler():
    """ Class for log handling
    """

    def __init__(self) -> None:
        os.makedirs(LOGS_DIRECTORY, exist_ok=True)
        self.log_file = os.path.join(LOGS_DIRECTORY, f'{APP_NAME}.log')

    def get_logger(self, name: str = APP_NAME) -> logging.Logger:
        logger = logging.getLogger(name)
        log_formatter = logging.Formatter("%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S",)

        # Suppress all logging errors
        logging.raiseExceptions = False
        logger.setLevel(logging.INFO)

        if not logger.hasHandlers():
            # adding console logger
            console_log_handler = logging.StreamHandler()
            console_log_handler.setFormatter(log_formatter)
            logger.addHandler(console_log_handler)

            # adding file logger, file will rotated after 10 MB and max file count is 5
            file_log_handler = RotatingFileHandler(filename=self.log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
            file_log_handler.setFormatter(log_formatter)
            logger.addHandler(file_log_handler)

        return logger


class CloudStorageHandler(ABC):
    """Abstract class for all cloud storage handler
    """
    @abstractmethod
    def upload(self, filepath: str) -> bool:
        pass

    @abstractmethod
    def purge(self) -> None:
        pass


class S3Handler(CloudStorageHandler):
    """ Child class of CloudStorageHandler to handle S3 operations
    """

    def __init__(self) -> None:
        self.logger = LogHandler().get_logger(name=__class__.__name__)

        session = boto3.Session(profile_name=AWS_PROFILE)
        self.s3_client = session.client('s3')

    def purge(self) -> None:
        # get current files in the bucket
        response = self.s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=S3_BACKUP_KEY_PREFIX)

        if 'Contents' in response:
            files = response['Contents']

            # Sort files by last modified date
            existing_files = sorted(files, key=lambda x: x['LastModified'])

            # If there are more than max_backup_files, delete the oldest ones
            if len(existing_files) > MAX_BACKUP_FILES:
                files_to_delete = existing_files[:len(existing_files) - MAX_BACKUP_FILES]
                for file in files_to_delete:
                    file_key = file['Key']
                    self.s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=file_key)
                    self.logger.info(f"Successfully purged old backup file from S3, s3://{S3_BUCKET_NAME}/{file_key}")

    def upload(self, filepath: str) -> bool:
        upload_status = False

        # checking if file exists
        if not os.path.exists(filepath):
            self.logger.warning(f'Cannot upload {filepath} to S3 as file {filepath} does not exists')
            return upload_status

        self.logger.info(f'Trying to uploading {filepath} to S3, bucket: {S3_BUCKET_NAME}')
        try:
            # Upload the backup file to S3
            s3_backup_key = f"{S3_BACKUP_KEY_PREFIX}{os.path.basename(filepath)}"
            self.s3_client.upload_file(filepath, S3_BUCKET_NAME, s3_backup_key)
            self.logger.info(f'Successfully uploaded file to S3, s3://{S3_BUCKET_NAME}/{s3_backup_key}')
            upload_status = True
        except Exception as e:
            self.logger.warning(f"Failed to upload file to S3, Error:{str(e)}")

        self.logger.info(f'Upload status: {upload_status}')
        return upload_status


class GDriveHandler(CloudStorageHandler):
    """ Child class of CloudStorageHandler to handle Google drive (gDrive) operations
    """

    def __init__(self) -> None:
        self.logger = LogHandler().get_logger(name=__class__.__name__)

        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE)
        self.gdrive_service = build('drive', 'v3', credentials=creds)

    def upload(self, filepath: str) -> bool:
        upload_status = False
        if not os.path.exists(filepath):
            self.logger.warning(f'Cannot upload {filepath} to google drive as file {filepath} does not exists')
            return upload_status

        self.logger.info(f'Trying to uploading {filepath} to google drive')
        try:
            # Setting the name of file in google drive
            file_metadata = {
                'name': os.path.basename(filepath),     # name of the target file on google drive
                'parents': [GOOGLE_DRIVE_FOLDER_ID]     # name of the folder on google drive where the file needs to be uploaded
            }

            # Trying to guess the MIME type of the file ; default is binary stream
            mime_type, _ = mimetypes.guess_type(filepath)
            if mime_type is None:
                mime_type = 'application/octet-stream'

            media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)

            # Upload the file
            request = self.gdrive_service.files().create(body=file_metadata, media_body=media, fields='id')

            # Execute upload in chunks
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    self.logger.info(f"Uploaded {int(status.progress() * 100)}%.")

            self.logger.info(f'Successfully uploaded file to google drive, file ID: {response.get("id")}')
            upload_status = True
        except Exception as e:
            self.logger.warning(f"Failed to upload file to google drive, Error: {str(e)}")

        self.logger.info(f'Upload status: {upload_status}')
        return upload_status

    def purge(self) -> None:
        query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
        results = self.gdrive_service.files().list(q=query, spaces='drive', fields="files(id, name, createdTime)", orderBy="createdTime desc").execute()
        existing_files = results.get('files', [])

        if len(existing_files) > MAX_BACKUP_FILES:
            for file in existing_files[MAX_BACKUP_FILES:]:  # Keep the MAX_BACKUP_FILES recent files
                self.gdrive_service.files().delete(fileId=file['id']).execute()
                self.logger.info(f"Successfully purged old backup file from google drive, file: {file['name']}")


class CpanelHandler():
    """ Class to interact with Cpanel
    """

    def __init__(self) -> None:
        self.logger = LogHandler().get_logger()

    def __get_backup_file(self) -> str:
        # Determine the backup file name pattern based on the format: backup-8.17.2024_17-46-55_{cpanel_username}.tar.gz
        regex_pattern = re.compile(rf"backup-\d{{1,2}}\.\d{{1,2}}\.\d{{4}}_\d{{2}}-\d{{2}}-\d{{2}}_{re.escape(CPANEL_USERNAME)}\.tar\.gz")
        backup_directory = Path(f"/home/{CPANEL_USERNAME}/")

        # Find the actual backup file
        self.logger.info(f'Looking for backup file under {backup_directory}')
        backup_filename = next((f for f in backup_directory.iterdir() if regex_pattern.match(f.name)), None)

        return backup_filename

    def __initiate_full_backup(self) -> None:
        self.logger.info('Initializing full backup creation in cPanel')

        # Create headers for authentication using the cPanel API Token
        headers = {
            "Authorization": f"cpanel {CPANEL_USERNAME}:{CPANEL_API_TOKEN}"
        }

        # # Create headers for authentication using the cPanel password
        # headers = {
        #     "Authorization": f"Bearer {CPANEL_USERNAME}:{CPANEL_PASSWORD}"
        # }

        # Define the API endpoint for backup creation using UAPI
        api_endpoint = f"{CPANEL_URL}/execute/Backup/fullbackup_to_homedir"

        # Set up the data payload for home directory backup
        payload = {
            "email": BACKUP_DESTINATION_EMAIL,
            "homedir": "include"
        }

        # Send the request to the cPanel API
        response = requests.post(api_endpoint, headers=headers, data=payload)

        if response.status_code != 200:
            self.logger.error(f'Received unexpected response code while creating backup file via API, expected=200; received={response.status_code}')
            return

        api_response = response.json()
        api_status = api_response.get("status")
        if api_status != 1:
            self.logger.error(f'Received unexpected status while creating backup file via API, expected=1; received={api_status}')
            return

        self.logger.info(f'Successfully initiated the full backup creation process')

    def run_backup(self) -> str:
        self.__initiate_full_backup()

        self.logger.info(f'Waiting for {BACKUP_CHECK_DELAY} seconds for full backup creation process to complete')
        time.sleep(BACKUP_CHECK_DELAY)

        backup_filename = self.__get_backup_file()
        if not backup_filename:
            self.logger.error(f'No backup file found, ensure that the backup process completed successfully')
            return

        self.logger.info(f'Backup file is {backup_filename}')
        return backup_filename


# driver code
if __name__ == '__main__':
    # making sure that user selects proper target lcoation
    parser = argparse.ArgumentParser()
    required_group = parser.add_argument_group('required arguments')
    required_group.add_argument('-t', '--target', choices=['gdrive', 's3'], help='cPanel backup target location', required=True, type=str)

    args = parser.parse_args()

    logger = LogHandler().get_logger()
    logger.info(f'Starting {APP_NAME} v{APP_VERSION}')
    logger.info(f'Target is {args.target}')

    # taking full backup
    cpanel_handler = CpanelHandler()
    backup_filename = cpanel_handler.run_backup()

    upload_status = False

    if args.target == 'gdrive':
        gdrive = GDriveHandler()
        upload_status = gdrive.upload(backup_filename)
        gdrive.purge()

    elif args.target == 's3':
        s3 = S3Handler()
        upload_status = s3.upload(backup_filename)
        s3.purge()

    # cleanup when upload is successful
    if upload_status:
        os.remove(backup_filename)
        logger.info(f'Cleaned up backup file {backup_filename}')

    logger.info('All done !')
