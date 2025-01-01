# cPanelBackupPlus
### Version 1.1
Author : Lakhya Jyoti Nath (ljnath)<br>
Date : August 2024 - January 2025<br>
Email : ljnath@ljnath.com<br>
Website : https://ljnath.com

#### Automated cPanel Full Backup to AmazonS3, Google Drive and more
Managing and safeguarding your website's data is crucial, but cPanel's native backup system requires manual intervention and doesn't provide an easy way to automatically store your backups in the cloud. This Python script addresses these limitations by fully automating the backup process and seamlessly integrating with Amazon S3 for cloud storage.

### Overview
This script is designed to automatically create a full backup of your cPanel hosting account and upload the backup file to an Amazon S3 bucket or Google Drive folder. By leveraging cPanel's API, the script triggers the generation of a complete backup, including all files, databases, and email accounts associated with your hosting account. Once the backup is created, the script locates the backup file and transfers it to a specified S3 bucket in your AWS account or folder in your Google drive.

### Key Features
1. **Automated Full Backup Creation**: The script interacts with the cPanel API to initiate a full backup of your hosting account, covering all essential data including website files, databases, and emails.
   
2. **Seamless Cloud Integration**: After the backup is generated, the script automatically uploads the backup file to a predefined Amazon S3 bucket and/or Google Drive folder. This ensures that your data is securely stored in the cloud, providing easy access and redundancy.

3. **Configuration via .env File**: All sensitive information such as cPanel credentials, S3 bucket details, Google drive folder details, and other configuration parameters. are stored in a .env file. This approach not only keeps your credentials secure but also makes it easy to configure and adjust the script settings as needed.

4. **Customizable Settings**: The script offers flexibility in its configuration. Users can modify settings such as the backup directory, the number of backups, the S3 upload location, and the google drive folder to suit their specific needs.

5. **Error Handling and Logging**: The script includes robust error handling to manage issues that may arise during the backup or upload process. It also logs key actions and errors, providing transparency and aiding in troubleshooting.


### How It Works
1. **Setup**: Configure the script by adding your cPanel and S3 bucket details to a .env file. This includes your cPanel URL, username, API token, and the S3 bucket name where backups will be stored. Add your AWS credentials in `~/.aws/credentials` file as shown below
    ```
    [aws-profile-name]
    aws_access_key_id = aws-client-id
    aws_secret_access_key = aws-client-secret
    ```

3. **Backup Initiation**: The script sends a request to the cPanel API to start a full backup of your hosting account. You can configure the script to notify you via email once the backup is initiated.

4. **Backup File Detection**: After the backup process completes, the script automatically detects the newly created backup file in your home directory.

5. **Cloud Upload**: The detected backup file is then uploaded to your specified Amazon S3 bucket or Google Drive folder depending the target which you have selected during script execution. The script can be configured to upload to a specific folder within the bucket and/or folder, allowing you to organize your backups efficiently.

6. **Completion and Notification**: Once the upload is complete, the script logs the successful backup and upload, and can also send a notification to inform you that the process was successful.  It also deletes the backup file from the home directory to free up space.

### Why Use This Script?
* **Automate a Time-Consuming Process**: Eliminate the need for manual backups and ensure your data is regularly and consistently backed up.
* **Enhanced Data Security**: By storing your backups in the cloud, you ensure that your data is safe, accessible, and redundant.
* **Ease of Use**: With simple configuration through the .env file, you can have the script up and running in minutes, with minimal setup required. You can set up a cron job to run this script at regular intervals.


### Conclusion
This Python script is an essential tool for anyone managing a cPanel-hosted website, offering peace of mind by automating the critical task of data backup and storage. Whether you're managing a single site or multiple accounts, this solution provides a reliable, efficient, and secure way to protect your data.


## Give a Star! ⭐️

If you find this repository useful, please give it a star.
Thanks in advance !

## License

Copyright © 2024-2025 [Lakhya's Innovation Inc.](https://ljnath.com) under the [MIT License](https://github.com/ljnath/cPanelBackupPlus/blob/master/LICENSE).
