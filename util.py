import multiprocessing
import os
import pickle

import election_message as electionMessage


def consume(shared_queue: multiprocessing.Queue):
    # Receive the serialized object from the queue and deserialize it
    serialized_object = shared_queue.get()
    complex_object = pickle.loads(serialized_object)
    return complex_object


def produce_election_message(shared_queue: multiprocessing.Queue, election_message: electionMessage.ElectionMessage):
    serialized_object = pickle.dumps(election_message)
    shared_queue.put(serialized_object)


def get_or_default(dictionary: dict(), key) -> int:
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
