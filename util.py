import pickle

def consume(shared_queue):
    # Receive the serialized object from the queue and deserialize it
    serialized_object = shared_queue.get()
    complex_object = pickle.loads(serialized_object)
    return complex_object

def produce(shared_queue, complex_object):
    # Serialize and put the complex object into the queue
    serialized_object = pickle.dumps(complex_object)
    shared_queue.put(serialized_object)