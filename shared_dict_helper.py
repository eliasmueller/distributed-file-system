from enum import Enum

class DictKey(Enum):
    peers = "peers"
    peer_ip_dict = "peer_ip_dict"
    groups = "groups"
    is_leader_in_one_group = "is_leader_in_one_group"
    leader_id = "leader_id"
    peer_file_state = "peer_file_state"
    peer_vector_clock = "peer_vector_clock"

def update_shared_dict(shared_dict, lock, key: DictKey, value):
    with lock:
        shared_dict[key.value] = value

def initialise_shared_dict(shared_dict, lock, device_info_dynamic):
    with lock:
        shared_dict['peers'] = device_info_dynamic.PEERS
        shared_dict['peer_ip_dict'] = device_info_dynamic.PEER_IP_DICT
        shared_dict['groups'] = device_info_dynamic.GROUPS
        shared_dict['is_leader_in_one_group'] = device_info_dynamic.IS_LEADER_IN_ONE_GROUP
        shared_dict['leader_id'] = device_info_dynamic.LEADER_ID
        shared_dict['peer_file_state'] = device_info_dynamic.PEER_file_state
        shared_dict['peer_vector_clock'] = device_info_dynamic.PEER_vector_clock
