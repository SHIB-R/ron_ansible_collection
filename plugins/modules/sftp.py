
from ansible.module_utils.basic import AnsibleModule
import paramiko

def sftp_file(module):
# Get parameters
    src = module.params.get('src')
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
            private_key = paramiko.RSAKey.from_private_key_file(private_key)
            ssh.connect(host, port=port,
                        username=username, pkey=private_key)
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
        if state == 'download':
            sftp.get(src, dest)
            result = {"changed": True, "msg": "File downloaded successfully"}
        elif state == 'upload':
            sftp.put(src, dest)
            result = {"changed": True, "msg": "File uploaded successfully"}
        else:
            result = {"changed": False, "msg": "Invalid state"}
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
        src=dict(type='str', required=True),
        dest=dict(type='str', required=True),
        state=dict(type='str', required=True, choices=['download', 'upload']),
        host=dict(type='str', required=True),
        port=dict(type='int', default=22),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True)
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

