import os
import yaml
import json
from collections import OrderedDict


def load_json(path):
    with open(path, 'r') as f:
        content = f.read()
        data = json.loads(content)
    return data

def save_as_json(data, path, indent=4):
    """Save dict as json"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

def load_yaml(path):
    with open(path, encoding='utf8') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data

def save_ordereddict_as_yaml(data, save_path, Dumper=yaml.SafeDumper):
    class OrderedDumper(Dumper):
        pass 

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items()
        )
    
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    with open(save_path, 'w') as outfile:
        yaml.dump(data, outfile, Dumper=OrderedDumper, default_flow_style=False, sort_keys=False)

def save_yaml(data, save_path):
    """
    Save the dictionary into a yaml file.

    Parameters
    ----------
    data : dict
        The dictionary contains all data.

    save_path : string
        Full path of the output yaml file.
    """
    if isinstance(data, OrderedDict):
        save_ordereddict_as_yaml(data, save_path)
    else:
        with open(save_path, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)

def append_to_yaml(data, save_path):
    if not os.path.exists(save_path):
        save_yaml(data, save_path)
    else:
        with open(save_path, 'a') as outfile:
            yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)