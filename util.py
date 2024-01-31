import multiprocessing
import os
import pickle

import election_message


def consume(election_queue: multiprocessing.Queue):
    # Receive the serialized object from the queue and deserialize it
    serialized_object = election_queue.get()
    complex_object = pickle.loads(serialized_object)
    return complex_object


def produce_election_message(election_queue: multiprocessing.Queue, message: election_message.ElectionMessage):
    serialized_object = pickle.dumps(message)
    election_queue.put(serialized_object)


def get_or_default(dictionary: dict, key) -> int:
    value = 0
    if key in dictionary:
        value = dictionary.get(key)
    return value


def get_folder_state(storage_path: str):
    return {f: os.path.getmtime(os.path.join(storage_path, f)) for f in
            os.listdir(storage_path)}


def delete_file(filename: str, storage_path: str):
    filepath_file = f"{storage_path}/{filename}"
    if os.path.exists(filepath_file):
        os.remove(filepath_file)


def compare_vector_clocks(left_message, right_message):
    l_filename, l_vector_clock, l_temp_filename, l_sender_id, l_message_type, l_original_sender_id = left_message
    r_filename, r_vector_clock, r_temp_filename, r_sender_id, r_message_type, r_original_sender_id = right_message

    difference = 0
    for key, value in l_vector_clock.items():
        difference = difference + value - get_or_default(r_vector_clock, key)

    if difference < 0:
        return -1
    elif difference > 0:
        return 1
    else:
        return -1
    # return difference / abs(difference)
