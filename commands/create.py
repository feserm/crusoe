import os
import logging

from openstack.connection import Connection

from utils.yaml_reader import read_configuration
from utils.openstack_provider import OpenstackProvider

from icecream import ic

KEY_FOLDER = '~/.ssh'

def create(config_path: str):
    logging.info(f"\tCreating infrastructure with config file {config_path}")
    crusoe_config: dict = read_configuration(config_path)
    
    conn = OpenstackProvider.get_connection()
    
    subnet = conn.get_subnet(name_or_id=crusoe_config.get('subnet'))
    network = conn.get_network(name_or_id=subnet.get('network_id'))
    floating_ip = conn.get_floating_ip(id=crusoe_config.get('floating_ip'))    
    logging.info(f"\tFound network {network.get('name')} with subnet {subnet.get('name')} and floating IP {floating_ip.get('floating_ip_address')}")
    
    ssh_key = conn.get_keypair(name_or_id=crusoe_config.get('sshKey'))
    logging.info(f"\tUsing SSH key {ssh_key.get('name')} from {os.path.expanduser(KEY_FOLDER)}")
    
    sec_group = generate_sec_groups(conn)
    
    for idx in range(0,len(crusoe_config.get('instances'))):
        instance = crusoe_config.get('instances')[idx]
        logging.info(f"\tInstances ({idx+1}/{len(crusoe_config.get('instances'))}): Creating instance '{instance.get('name')}'")
        if idx==0:
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
        else:
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
        logging.info(f"\tCreated with private IP {server.private_v4}")

def generate_sec_groups(conn: Connection):
    sec_group = conn.get_security_group(name_or_id="[Crusoe] defaults")
    if sec_group:
        logging.info(f"\tSecurity group '{sec_group.get('name')}' already existed. Skipping creation.")
        return sec_group
    sec_group = conn.create_security_group(name="[Crusoe] defaults", description="Default security group for Crusoe")
    rules =[{
            "direction": "ingress", 
            "ethertype": "IPv4", 
            "protocol": None, 
            "port_range_min": None,
            "port_range_max": None, 
            "remote_ip_prefix": None, 
            "remote_group_id": sec_group.get('id')
        },{
            "direction": "ingress", 
            "ethertype": "IPv4", 
            "protocol": "tcp", 
            "port_range_min": 22,
            "port_range_max": 22, 
            "remote_ip_prefix": "0.0.0.0/0",
            "remote_group_id": None
    }]
    for rule in rules:
        conn.create_security_group_rule(sec_group.get('id'), **rule)
    logging.info(f"\tCreated security group '{sec_group.get('name')}' with ID {sec_group.get('id')}")
    return sec_group