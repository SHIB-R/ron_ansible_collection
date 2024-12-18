# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Konstantinos Georgoudis <kgeor@blacklines.gr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
collection: barak
module: sftp

short_description: download and upload 

version_added: "1.2.5"

description:
    - Use to upload and download files to or from sftp server, can be used with wildcards(*).

options:
    src_dir:
    description:
            - The source directory of the file\s. For downloads, this is the remote file path on the SFTP server. For uploads, this is the local file path.
    required: true
    type: str

    src_files:
    description:
            - The file\s you want to upload or download, can be used with Wildcard(*) and can be a list of files.
    required: true
    type: list

    dest:
        description:
            - The destination file path. For downloads, this is the local file path. For uploads, this is the remote file path on the SFTP server.
        required: true
        type: str

    state:
        description:
            - Specifies the action to perform. It can be either 'download' or 'upload'.
        required: true
        type: str
        choices:
            - download
            - upload
    host:
        description:
            - The IP address or the FQDN of the remote SFTP host.
        required: true
        type: str

    port:
        description:
            - The TCP port of the remote SFTP host. The default port is 22.
        type: int
        default: 22

    username:
        description:
            - Username for the SFTP connection.
        required: true
        type: str

    password:
        description:
            - Password for the SFTP connection. Required if 'private_key' is not provided.
        type: str
        no_log: true
        default: None

    private_key:
        description:
            - Path to the private key file for key-based authentication. Required if 'password' is not provided.
        type: str
        default: None

requirements:
    paramiko>=2.7.2
    os
    re
    glob
    fnmatch

'''

EXAMPLES = r'''

---
- name: SFTP File Transfer Example
  hosts: localhost
  gather_facts: no
  tasks:
    - name: Download file from SFTP server
      shib_r.barak.sftp:
        src_dir: /remote/path/to/
        src_files: file.txt
        dest: /local/path/to/save/file.txt
        state: download
        host: sftp.example.com
        port: 5522
        username: my_user
        password: my_password

    - name: Upload all files from path to SFTP server (using a key to connect)
      shib_r.barak.sftp:
        src_dir: /local/path/to/upload/
        src_files:
            - file_1
            - file_2
            - *file_pattern*
        dest: /remote/path/to/save/
        state: upload
        host: sftp.example.com
        username: my_user
        private_key: /path/to/private_key
      delegate_to: localhost
  
'''


from ansible.module_utils.basic import AnsibleModule
import paramiko
import os
import re
import glob
import fnmatch


def sftp_file(module):
# Get parameters
    src_dir = module.params.get('src_dir') 
    src_files = module.params.get('src_files')
    dest = module.params.get('dest')
    state = module.params.get('state')
    host = module.params.get('host')
    port = module.params.get('port')
    username = module.params.get('username')
    password = module.params.get('password')
    private_key = module.params.get('private_key')


# Initialize SSH client
    ssh = paramiko.SSHClient()
# Automatically add the server's host key (not secure, but useful for testing)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# if private key exists use it. use connect using password.
    try:
        if private_key:
            ssh.connect(host, port=port,
                        username=username, password=password, key_filename=private_key, allow_agent=True)
        else:
            ssh.connect(host, 
                        port=port,
                        username=username,
                        password=password)
    except Exception as e:
# If connection fails, return an error message and exit
        module.fail_json(msg=f"Failed to connect to {host}: {str(e)}")

# Start SFTP operation.
    try:
# Open SFTP session
        sftp = ssh.open_sftp()
        for item in src_files:
            if '*' in item: #if the filename has a wildcard in it
## Handle multiple files
# Set the directory to list files from
                from_dir = src_dir if src_dir else os.path.dirname(item)
                regex_pattern = re.compile(fnmatch.translate(item))
                from_full_path = os.path.join(src_dir, item)
# Download
                if state == 'download':
                    from_files_download = sftp.listdir(from_dir)
# Filter files that match the wildcard pattern
                    files_to_download = [file for file in from_files_download if regex_pattern.match(file)]
                    if not files_to_download:
                        module.fail_json(msg=f"No files match the pattern {item}")

                    for file in files_to_download:
                        remote_file_path = os.path.join(os.path.dirname(from_dir), file)
# Ensure dest is treated as a directory
                        local_file_path = os.path.join(dest, file) if os.path.isdir(dest) else dest
                 
                        try:
                            sftp.get(remote_file_path, local_file_path)
                        except Exception as e:
                            module.fail_json(msg=f"Failed to download {remote_file_path}: {str(e)}")
# Upload
                elif state == 'upload':
                    from_files_upload = os.listdir(from_dir)
# Use glob to find files matching the pattern locally
                    files_to_upload = [file for file in from_files_upload if regex_pattern.match(file)]
                    print(f"Matching files for upload: {files_to_upload}")
                    if not files_to_upload:
                        module.fail_json(msg=f"No files match the pattern {item}")

                    for file in files_to_upload:
                        local_file_path = os.path.join(from_dir, file)
                        remote_file_path = os.path.join(dest, file) if os.path.isdir(dest) else dest
                        try:
                           sftp.put(local_file_path, remote_file_path)
                        except Exception as e:
                            module.fail_json(msg=f"Failed to upload {local_file_path}: {str(e)}")

                else:
                    result = {"changed": False, "msg": "Invalid state"}
            else: # if the filename has no wildcard in it
                if state == 'download':
                    remote_file_path = from_full_path
                    local_file_path = os.path.join(dest, item) if os.path.isdir(dest) else dest
                    try:
                         sftp.get(remote_file_path, local_file_path)
                    except Exception as e:
                        module.fail_json(msg=f"Failed to download {remote_file_path}: {str(e)}")

                elif state == 'upload':
                    local_file_path = from_full_path
                    remote_file_path = os.path.join(dest, item) if os.path.isdir(dest) else dest
                    
                    try:
                        sftp.put(local_file_path, remote_file_path)
                    except Exception as e:
                        module.fail_json(msg=f"Failed to upload {local_file_path}: {str(e)}")

        result = {"changed": True, "msg": "Operation completed successfully"}

    except Exception as e:
# If an SFTP operation fails, return an error message and exit
            module.fail_json(msg=f"Failed to perform SFTP operation: {str(e)}")
    finally:
# Make sure session is closed.
        sftp.close()
        ssh.close()

    return result

# Get parameters
def main():
# Define the module's argument specification
    module_args = dict(
        src_dir=dict(type='str', required=True),
        src_files=dict(type='list', required=True),
        dest=dict(type='str', required=True),
        state=dict(type='str', required=True, choices=['download', 'upload']),
        host=dict(type='str', required=True),
        port=dict(type='int', default=22),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        private_key=dict(type='str', default=None)
    )

# Initialize Ansible module
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

# Start sftp_file function and print results.
    result = sftp_file(module)
    module.exit_json(**result)

if __name__ == '__main__':
    main()

