import os
import logging

from openstack.connection import Connection

from utils.yaml_reader import read_configuration
from utils.openstack_provider import OpenstackProvider
from utils.ansible_configurator import AnsibleConfigurator

from icecream import ic

KEY_FOLDER = '~/.ssh'
INVENTORY_FILE = '.ansible/inventory.ini'
JH_INI = '.ansible/jumphost.ini'

def create(config_path: str, log: logging.Logger):
    log.info(f"\tCreating infrastructure with config file {config_path}")
    crusoe_config: dict = read_configuration(config_path, log)
    
    conn = OpenstackProvider.get_connection()
    
    # check if the network, subnet and floating IP exist
    subnet = conn.get_subnet(name_or_id=crusoe_config.get('subnet'))
    network = conn.get_network(name_or_id=subnet.get('network_id'))
    floating_ip = conn.get_floating_ip(id=crusoe_config.get('floating_ip'))    
    log.info(f"\tFound network {network.get('name')} with subnet {subnet.get('name')} and floating IP {floating_ip.get('floating_ip_address')}")
    
    # get the ssh key
    ssh_key = conn.get_keypair(name_or_id=crusoe_config.get('sshKey'))
    log.info(f"\tUsing SSH key {ssh_key.get('name')} from {os.path.expanduser(KEY_FOLDER)}")
    
    # create the security group if needed
    sec_group = generate_sec_groups(conn, log)
    
    with open(INVENTORY_FILE, 'w') as f:
        f.write('')
    for idx in range(0,len(crusoe_config.get('instances'))):
        instance = crusoe_config.get('instances')[idx]
        log.info(f"\tInstances ({idx+1}/{len(crusoe_config.get('instances'))}): Creating instance '{instance.get('name')}'")
        # create the instance
        if idx==0:
            # create the proxy acting also as a jumphost with a floating IP
            server = conn.create_server(
                name=instance.get('name'),
                image=instance.get('image'),
                flavor=instance.get('type'),
                ips=[crusoe_config.get('floating_ip')],
                network=network,
                key_name=ssh_key.get('name'),
                security_groups=[sec_group.get('name')],
                wait=True
            )
            # write JH_INI file to allow installation of ansible on the jumphost
            with open(JH_INI, 'w') as f:
                f.write(f"[jumphost]\n{floating_ip.get('floating_ip_address')} ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/{ssh_key.get('name')} ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
        else:
            # create the other instances
            server = conn.create_server(
                name=instance.get('name'),
                image=instance.get('image'),
                flavor=instance.get('type'),
                network=network,
                ips=[],
                auto_ip=False,
                key_name=ssh_key.get('name'),
                security_groups=[sec_group.get('name')],
                wait=True
            )
        log.info(f"\tCreated with private IP {server.private_v4}")
        with open(INVENTORY_FILE, 'a') as f:
            f.write(f"[{instance.get('name')}]\n{server.private_v4} ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/{ssh_key.get('name')} ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
    log.info(f"\tAll instances created. Configuring Ansible")
    
    # configure the hosts using ansible playbooks
    ansibleConfigurator = AnsibleConfigurator(JH_INI, INVENTORY_FILE, log)
    ansibleConfigurator.install_on_jumphost()
    # TODO: either run all playbooks through a main playbook or run them in a loop
    ansibleConfigurator.configure('playbooks/custom/main.yml', f"{os.path.expanduser(KEY_FOLDER)}/{ssh_key.get('name')}")
    log.info(f"\tInfrastructure created and configured")

def generate_sec_groups(conn: Connection, log: logging.Logger):
    sec_group = conn.get_security_group(name_or_id="[Crusoe] defaults")
    if sec_group:
        log.info(f"\tSecurity group '{sec_group.get('name')}' already existed. Skipping creation.")
        return sec_group
    sec_group = conn.create_security_group(name="[Crusoe] defaults", description="Default security group for Crusoe")
    rules =[{
        # allow all traffic within the security group
            "direction": "ingress", 
            "ethertype": "IPv4", 
            "protocol": None, 
            "port_range_min": None,
            "port_range_max": None, 
            "remote_ip_prefix": None, 
            "remote_group_id": sec_group.get('id')
        },{
        # allow SSH from anywhere
            "direction": "ingress", 
            "ethertype": "IPv4", 
            "protocol": "tcp", 
            "port_range_min": 22,
            "port_range_max": 22, 
            "remote_ip_prefix": "0.0.0.0/0",
            "remote_group_id": None
    },{
        # allow HTTP from anywhere
            "direction": "ingress", 
            "ethertype": "IPv4", 
            "protocol": "tcp", 
            "port_range_min": 80,
            "port_range_max": 80, 
            "remote_ip_prefix": None
    },{
        # allow HTTPS from anywhere
            "direction": "ingress", 
            "ethertype": "IPv4", 
            "protocol": "tcp", 
            "port_range_min": 443,
            "port_range_max": 443, 
            "remote_ip_prefix": None
    }]
    for rule in rules:
        conn.create_security_group_rule(sec_group.get('id'), **rule)
    log.info(f"\tCreated security group '{sec_group.get('name')}' with ID {sec_group.get('id')}")
    return sec_group