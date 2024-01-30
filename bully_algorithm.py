import multiprocessing
from multiprocessing.managers import DictProxy
import datetime
import time
import uuid
from typing import List

import message_formater as formater
import deviceInfo
import electionMessage
import sender as bSend
from shared_dict_helper import DictKey
import shared_dict_helper
import util

import broadcast_listener as bListen
import discovery

class BullyAlgorithm(multiprocessing.Process):
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                 shared_queue: multiprocessing.Queue,
                 shared_dict: DictProxy,
                 lock):
        super(BullyAlgorithm, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        self.shared_dict = shared_dict
        # Init Bully Properties
        self.peer_id = device_info_static.PEER_ID
        self.leader_id = None
        self.is_leader = False
        self.is_running = True
        self.election_id = None
        self.received_higher_election_inquiry = []
        self.received_lower_election_inquiry = []
        self.lock = lock
        self.run()

    def get_device_info_dynamic(self):
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        self.leader_id = self.device_info_dynamic.LEADER_ID
        if not self.shared_queue.empty():
            queue_message = util.consume(self.shared_queue)
            self.handle_election_message(queue_message)
    
    def update_device_info_dynamic(self, message: electionMessage.ElectionMessage):
        if message.SENDER_ID not in self.device_info_dynamic.PEERS:
            self.device_info_dynamic.PEERS.append(message.SENDER_ID)
        self.device_info_dynamic.PEER_IP_DICT[message.SENDER_ID] = message.SENDER_IP
        self.device_info_dynamic.LEADER_ID = self.leader_id
        self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)

    def run(self):
        while self.is_running:
            self.get_device_info_dynamic()
            if (not self.is_leader) & (not self.leader_id) & (not self.election_id):
                self.election()

    def election(self):
        # Election ID is used to identify election messages and to show, this instance is currently running an election.
        self.election_id = str(uuid.uuid4())
        print(f"Process {self.peer_id} initiates election with election id {self.election_id}.")

        # Reset State that might be altered by other methods
        self.is_leader = False
        self.leader_id = None
        self.received_higher_election_inquiry = []
        self.received_lower_election_inquiry = []

        filtered = filter(lambda x: self.peer_id < x, self.device_info_dynamic.PEERS)
        peers_with_higher_peer_id = list(filtered)

        for peer_id in peers_with_higher_peer_id:
            # Send election message to higher numbered processes
            print(f"Process {self.peer_id} sends election message to Process {peer_id}.")
            self.send_election_inquiry(recipient_id=peer_id, recipient_ip=None)

        result = self.wait_for_election_responses(peers_with_higher_peer_id)

        if result == "timeout":
            print(f"Process {self.peer_id} did not receive any response. Declares itself as leader.")
            self.leader_id = self.peer_id
            self.is_leader = True
            self.send_election_leader()
            self.election_id = None
            self.device_info_dynamic.LEADER_ID = self.leader_id
            shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.leader_id, self.leader_id)

        else:
            print(f"Process {self.peer_id} is aborting election {self.election_id}.")
            self.received_lower_election_inquiry = []
            self.received_higher_election_inquiry = []
            if result == "higher":
                self.wait_for_peer_to_declare_as_leader()
            else:
                self.election_id = None

    def wait_for_election_responses(self, peers_with_higher_peer_id: List[int]) -> str:
        now = datetime.datetime.now()
        if not peers_with_higher_peer_id:
            timeout = now + datetime.timedelta(seconds=3)  # exit early if it is the highest peer, not 0 to ensure "leader" message arrives after "answer"
        else:
            timeout = now + datetime.timedelta(seconds=15)

        result = "timeout"
        while now < timeout:
            self.get_device_info_dynamic()
            now = datetime.datetime.now()
            if self.received_lower_election_inquiry:
                result = "lower"
                break
            if self.received_higher_election_inquiry:
                result = "higher"
                break
            time.sleep(0.1)
        return result

    # Waiting for some time until the higher process declares itself as leader, otherwise start another process
    def wait_for_peer_to_declare_as_leader(self):
        now = datetime.datetime.now()
        timeout = now + datetime.timedelta(seconds=20)
        while now < timeout:
            self.get_device_info_dynamic()
            now = datetime.datetime.now()
            if self.leader_id:
                break
            if self.received_lower_election_inquiry:
                break
            time.sleep(0.1)
        self.received_higher_election_inquiry = []
        self.received_lower_election_inquiry = []
        self.election_id = None

    def send_election_inquiry(self, recipient_id: int, recipient_ip: None):
        if not recipient_ip:
            ip = self.device_info_dynamic.PEER_IP_DICT[recipient_id]
        else:
            ip = recipient_ip
        message = formater.get_election_message(self.device_info_static, "inquiry", self.election_id)
        bSend.basic_broadcast(ip=ip, port=self.device_info_static.LAN_BROADCAST_PORT, message=message)

    def respond_to_election(self, requesting_peer_id: int, requesting_peer_ip: str, election_id: str):
        print(f"Process {self.peer_id} receives election message from process {requesting_peer_id}, with election id {election_id}, answers ACK.")
        message = formater.get_election_message(self.device_info_static, "answer", election_id)
        bSend.basic_broadcast(ip=requesting_peer_ip, port=self.device_info_static.LAN_BROADCAST_PORT, message=message)

    def send_election_leader(self):
        message = formater.get_election_message(self.device_info_static, "leader", self.election_id)
        bSend.basic_broadcast(self.device_info_static.LAN_BROADCAST_IP, self.device_info_static.LAN_BROADCAST_PORT,
                              message)

    def handle_election_message(self, message: electionMessage.ElectionMessage):
        self.leader_id = None
        self.is_leader = False
        # this is always from a lower process:
        if message.MESSAGE_SPECIFICATION == " inquiry":
            self.respond_to_election(message.SENDER_ID, message.SENDER_IP, message.ELECTION_ID)
            if self.election_id:
                print(f"Process {self.peer_id} received inquiry from lower process {message.SENDER_ID}. {self.peer_id} has already an election ongoing, will abort it and start new one. Old election ID: {self.election_id}")
                self.received_lower_election_inquiry.append(message.SENDER_ID)
            else:
                print(f"Process {self.peer_id} received inquiry from lower process {message.SENDER_ID}. Starting new election.")

        # Only handle answers for the own election, also only possible from higher processes, as only those receive inquiry:
        elif (message.MESSAGE_SPECIFICATION == " answer") & (self.election_id == message.ELECTION_ID):
            print(f"Process {self.peer_id} received answer from higher process {message.SENDER_ID}. Aborting possible own elections.")
            self.leader_id = None
            self.is_leader = False
            self.received_higher_election_inquiry.append(message.SENDER_ID)

        elif message.MESSAGE_SPECIFICATION == " leader":
            if message.SENDER_ID < self.peer_id:
                self.leader_id = None
                self.is_leader = False
                if self.election_id:
                    print(
                        f"Process {self.peer_id} received leader from lower process {message.SENDER_ID}. {self.peer_id} has already an election ongoing, will abort it and start new one. Old election ID: {self.election_id}.")
                    self.received_lower_election_inquiry.append(message.SENDER_ID)
                else:
                    print(f"Process {self.peer_id} received leader from lower process {message.SENDER_ID}. Starting new election.")
            elif message.SENDER_ID > self.peer_id:
                print(f"Process {self.peer_id} received leader message from higher process {message.SENDER_ID}. Accepting him.")
                self.received_higher_election_inquiry.append(message.SENDER_ID)
                self.is_leader = False
                self.leader_id = message.SENDER_ID
                
        self.update_device_info_dynamic(message)
