import os
from openstack import config
from openstack.connection import Connection

CLOUDS_YAML_PATH = '~/.config/crusoe/clouds.yaml'

class OpenstackProvider:
    def get_connection():
        cloud_config = config.OpenStackConfig(config_files=[os.path.expanduser(CLOUDS_YAML_PATH)])
        cloud = cloud_config.get_one(cloud='openstack')

        conn = Connection(config=cloud)
        return conn