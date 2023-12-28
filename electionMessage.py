class ElectionMessage:
    def __init__(self, sender_id: int, message_specification: str, election_id: str, sender_ip: str):
        self.SENDER_ID = sender_id
        self.MESSAGE_SPECIFICATION = message_specification
        self.ELECTION_ID = election_id
        self.SENDER_IP = sender_ip
