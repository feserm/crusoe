import os
import yaml
import logging

def read_configuration(path):
    try:
        with open(os.path.expanduser(path), 'r') as stream:
            return yaml.safe_load(stream)
    except FileNotFoundError:
        logging.error(f"File {path} not found")
        exit(1)