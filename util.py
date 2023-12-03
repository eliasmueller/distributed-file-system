import pickle

import multiprocessing
import deviceInfo as deviceInfo

def consume(shared_queue: multiprocessing.Queue) -> deviceInfo.DeviceInfoDynamic:
    # Receive the serialized object from the queue and deserialize it
    serialized_object = shared_queue.get()
    complex_object = pickle.loads(serialized_object)
    return complex_object

def produce(shared_queue: multiprocessing.Queue, complex_object: deviceInfo.DeviceInfoDynamic):
    # Serialize and put the complex object into the queue
    serialized_object = pickle.dumps(complex_object)
    shared_queue.put(serialized_object)