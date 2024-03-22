import logging
from icecream import ic
import os
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import subprocess

class AnsibleConfigurator():
    def __init__(self, jh_ini: str, inventory_file: str, log: logging.Logger):
        self.jh_ini = jh_ini
        self.inventory_file = inventory_file
        self.log = log

    def configure(self, playbook: str, ssh_key: str):
        with open(self.jh_ini, 'r') as f:
            jh = f.read().split('\n')[1].split(' ')
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.load_system_host_keys()
        ssh.connect(jh[0], username=jh[1].split('=')[1], key_filename=os.path.expanduser(jh[2].split('=')[1]))
        ssh.exec_command('mkdir -p /home/ubuntu/.ansible')
        # create the tar ball from a subdirectory of playbooks called custom
        subprocess.run(["tar", "-czf", "custom.tar.gz", "-C", "playbooks", "custom"])
        
        # copy the playbook and ssh key to the jumphost
        scp = SCPClient(ssh.get_transport())
        scp.put('custom.tar.gz', '/home/ubuntu/.ansible')
        ssh.exec_command('tar -xzf /home/ubuntu/.ansible/custom.tar.gz -C /home/ubuntu/.ansible')
        ssh.exec_command('mv /home/ubuntu/.ansible/custom/* /home/ubuntu/.ansible')
        subprocess.run(["rm", "custom.tar.gz"])
        scp.put(playbook, '/home/ubuntu/.ansible')
        scp.put(self.inventory_file, '/home/ubuntu/.ansible')
        scp.put(ssh_key, '/home/ubuntu/.ssh')
        
        # run the playbook
        cmd = f"ansible-playbook /home/ubuntu/.ansible/{playbook.split('/')[-1]} -i /home/ubuntu/.ansible/{self.inventory_file.split('/')[-1]};"
        _, stdout, stderr = ssh.exec_command(cmd)
        for line in stdout:
            self.log.info(line.strip('\n'))
            
        for line in stderr:
            self.log.error(line.strip('\n'))

        scp.close()
        ssh.close()
        
    def install_on_jumphost(self):
        #TODO: move .ansible to ~/.ansible
        #TODO: find a more pythontic way to do this
        subprocess.run(["ansible-playbook", "playbooks/crusoe/01_install_ansible.yml", "-i", f"{os.path.expanduser('.ansible/jumphost.ini')}"])