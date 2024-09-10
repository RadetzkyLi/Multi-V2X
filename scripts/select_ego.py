# Due to red lights, some CAVs may keep static for the whole sequence,
# therefore, they are not suitable for being ego. 
# Here, we select as candidate ego the CAVs that move at least 15s.
# One can customize his/her selection by accessing global movement info,
# map info and so on.
#
# @author: Rongsong Li
# @email: rongsong.li@qq.com
# @dates: 2023-11-15

# ================================================================
# - imports
# ================================================================
import os
import sys

import numpy as np
import pandas as pd
import logging
import glob
import argparse
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from common_utils.fileio import load_yaml, save_as_json

# ================================================================
# - basic functions
# ================================================================
def calc_scalar_speed(speed):
    """Calculate scalar speed
    Paramters
    ---------
    speed: List[float]
        Speed of various directions. We assume these directions are predpendicular
        to each other.
    Returns
    -------
    s: float
        Scalar speed.
    """
    s = 0
    for el in speed:
        s += el**2
    s = s**0.5
    return s

def calc_distance(speed_list, freq=10):
    """Calculate total distance based on speed list and sampling frequency.
    We assume the object are in constant speed or acceleration between two
    steps.
    
    """
    N = len(speed_list)
    if N <= 1:
        return 0.0
    delta_t = 1.0/freq
    d = 0
    for i in range(1,N):
        v = (speed_list[i] + speed_list[i-1])/2.0
        d += v*delta_t
    return d

def calc_avg_speed(speed_list, freq=10):
    d = calc_distance(speed_list, freq)
    if d<=0.1:
        return 0,0
    else:
        total_time = (len(speed_list)-1)/freq
        return d/total_time, d

# ================================================================
# - utility functions
# ================================================================
def is_vehicle_moving(speed, thr=2.0):
    """Judge whether the object is moving (i.e., speed > thr m/s)
    
    Parameters
    ----------
    speed: List[float]|float
        Vector speed or scalar speed
    
    Returns
    -------
    flag: bool
        
    """
    if isinstance(speed, float):
        v = speed
    else:
        v = calc_scalar_speed(speed)
    return v>=thr

def get_frame_from_path(path, to_int=False):
    fname = os.path.basename(path)
    fname = fname.split(".")[0]
    frame = fname.split("_")[0]
    if to_int:
        frame = int(frame)
    return frame

def get_scenario_name_from_path(root):
    return os.path.basename(os.path.dirname(os.path.join(root, 'tmp')))

def get_cav_list_from_scenario(scenario_root):
    """Get all cavs from given scenario root
    
    Parameters
    ----------
    scenario_root: str
        Scenario dataset root
    Returns
    -------
    cav_list: List[int]
        All cav ids.
    """
    cav_list = []
    for agent in os.listdir(scenario_root):
        if agent.startswith("cav"):
            cav_list.append(agent.split("cav_")[1])

    cav_list = [int(cav) for cav in cav_list]
    return cav_list

def get_rsu_list_from_scenario(scenario_root):
    """Get all rsus from given scenario root.

    Parameters
    ----------
    scenario_root: str

    Returns
    -------
    rsu_list: List[int]
    
    """
    rsu_list = []
    for agent in os.listdir(scenario_root):
        if agent.startswith("rsu"):
            rsu_list.append(agent.split("rsu_")[1])

    rsu_list = [int(rsu) for rsu in rsu_list]
    return rsu_list

def get_objects_moving_info(scenario_root, target_objects=[], save_dir=None, thr_speed=2.0):
    """Get objects' moving information, including moving distance, average speed.
    
    Parameters
    ----------
    scenario_root: str
        Dir of scenario dataset
    target_objects: List[int]
        Ids of objects that we want to count on.
    save_dir: str
        If not None, the resulted df will be saved in "save_dir/{scenario_name}_move.xlsx".
    thr_speed: float
        If scalar speed of a object is greater than `thr_speed`, it is regarded as moving at
        that timestep.

    Returns
    -------
    df: pd.DataFrame
        With columns ['obj', 'type', 'srt', 'frames', 'moving_frames', 'distance', 
                    'avg_speed', 'min_speed', 'max_speed'].
    """
    obj_info = {obj: {"speed": [], "srt": None, "frames": 0, "moving_frames": 0, "type": None} 
                for obj in target_objects}

    # get movement info
    pattern = os.path.join(scenario_root, "map", "*.yaml")
    paths = glob.glob(pattern)
    paths.sort()
    for path in tqdm(paths):
        scene_info = load_yaml(path)
        if len(target_objects) > 0:
            # count only target objects
            for obj in target_objects:
                if obj in scene_info["objects"]:
                    v = calc_scalar_speed(scene_info["objects"][obj]['speed'])
                    obj_info[obj]["speed"].append(v)
                    if obj_info[obj]["srt"] is None:
                        obj_info[obj]["srt"] = get_frame_from_path(path)
                    if obj_info[obj]["type"] is None:
                        obj_info[obj]["type"] = scene_info["objects"][obj]["category"]
                    obj_info[obj]['frames'] += 1
                    obj_info[obj]['moving_frames'] += 1 if is_vehicle_moving(v, thr_speed) else 0
        else:
            # count all objects
            for obj,info in scene_info["objects"].items():
                v = calc_scalar_speed(scene_info["objects"][obj]['speed'])
                if obj not in obj_info:
                    obj_info[obj] = {"speed": [], 
                                     "srt": get_frame_from_path(path), 
                                     "frames": 0, 
                                     "moving_frames": 0,
                                     "type": scene_info["objects"][obj]["category"]
                                     }
                obj_info[obj]["speed"].append(v)
                obj_info[obj]['frames'] += 1
                obj_info[obj]['moving_frames'] += 1 if is_vehicle_moving(v, thr_speed) else 0
    
    
    # stats
    cnt = 0
    cav_list = get_cav_list_from_scenario(scenario_root)
    df = pd.DataFrame(columns=["obj", "type", "is_cav", "srt", "frames", "moving_frames", "distance", 
                               "avg_speed", "min_speed", "max_speed"])
    for obj,info in obj_info.items():
        avg_s,d = calc_avg_speed(info['speed'])
        is_cav = 'Y' if obj in cav_list else 'N'
        df.loc[cnt] = [obj, info['type'], is_cav, info['srt'], info['frames'], info['moving_frames'], d, 
                       avg_s, np.min(info['speed']), np.max(info['speed'])]
        cnt += 1
    
    scenario_name = get_scenario_name_from_path(scenario_root)
    logging.info("{0} objects are counted in scenario {1}".format(cnt, scenario_name))
    if save_dir is not None:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        path = os.path.join(save_dir, scenario_name+"_move.xlsx")
        df = df.round({"distance": 3, "avg_speed": 3, "min_speed": 3, "max_speed": 3})
        df.to_excel(path, index=False)

    return df

def get_scenario_ego_candidates(scenario_root, thr_speed=2.0):
    """CAVs that are moving at least half of the time are regarded as ego."""
    cav_list = get_cav_list_from_scenario(scenario_root)
    df = get_objects_moving_info(scenario_root, cav_list, thr_speed=thr_speed)
    ego_cands = []
    thr_ratio = 0.5
    min_frames = 20
    for _,row in df.iterrows():
        if row.loc['frames']>min_frames and row.loc['moving_frames']>=row.loc['frames']*thr_ratio:
            ego_cands.append(row.loc['obj'])

    logging.info("{0} out of {1} CAVs are taken as ego candidates"
                 .format(len(ego_cands), len(cav_list)))
    logging.info("All ego candidates: {0}".format(ego_cands))

    return ego_cands

def get_speed_in_one_scenario(scenario_root):
    """Get (scalar) speed of each objects at each frame in 
    a scenario and save them in a pd.DataFrame."""
    base_dir = os.path.join(scenario_root, "map")
    if not os.path.exists(base_dir):
        raise ValueError("There is no movement recording in given"\
                         " dir: {0}".format(base_dir))
    pattern = os.path.join(base_dir, "*.yaml")
    paths = glob.glob(pattern)
    paths.sort()

    # read yaml file 
    df = pd.DataFrame(columns=['object', 'category', 'frame'])


# ===========================================================
# - application
# ===========================================================
def get_dataset_moving_info(dataset_root, save_path):
    df_list = []
    key_list = []
    for scenario_name in os.listdir(dataset_root):
        scenario_root = os.path.join(dataset_root, scenario_name)
        df = get_objects_moving_info(scenario_root, save_dir=None)
        df_list.append(df)
        key_list.append(scenario_name)
    df = pd.concat(df_list, keys=key_list)
    if save_path is not None:
        df.to_excel(save_path)
    return df

def get_dataset_agent_and_ego_candidate(dataset_root, save_path=None):
    # structure: 
    # { scenario_name: {
    #     "cav_list": [], 
    #     "rsu_list": [], 
    #     "recommended_ego_cav_list": []
    #   }
    # }
    scenario_agents = {}

    for scenario_name in os.listdir(dataset_root):
        scenario_root = os.path.join(dataset_root, scenario_name)

        ego_cand_list = get_scenario_ego_candidates(scenario_root)
        cav_list = get_cav_list_from_scenario(scenario_root)
        rsu_list = get_rsu_list_from_scenario(scenario_root)

        scenario_agents[scenario_name] = {
            "cav_list": cav_list,
            "rsu_list": rsu_list,
            "recommended_ego_cav_list": ego_cand_list
        }

    if save_path is not None:
        save_as_json(scenario_agents, save_path)

    return scenario_agents

# ============================================================
# - running
# ============================================================
def get_options():
    argparser = argparse.ArgumentParser(
        description='Ego candidates selection')
    argparser.add_argument(
        '--root',
        help = 'scenario root'
        )
    argparser.add_argument(
        "--mode",
        default="auto",
        type=str,
        help="The method to select ego candidates, 'auto' or 'manual' supported."
    )
    argparser.add_argument(
        "--save-path",
        default=None,
        type=str,
        help="Path to save results."
    )
    argparser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Tell me what you are doing"
    )
    args = argparser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    return args

def main(args):
    if args.mode == 'manual':
        get_dataset_moving_info(args.root, args.save_path)
    elif args.mode == 'auto':
        get_dataset_moving_info(args.root, args.save_dir)
    else:
        raise ValueError("Unsupported `mode`='{0}'".format(args.mode))

if __name__ == '__main__':
    args = get_options()
    main(args)
    
