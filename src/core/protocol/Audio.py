from src.core.protocol.FromClient import FromClientPacket


class AudioPacket(FromClientPacket):
    def __init__(self, encoded_audio: bytes):
        self.encoded_audio = encoded_audio

    @staticmethod
    def get_id() -> str:
        return __class__.__name__

    def serialize(self) -> bytes:
        return self.encoded_audio

    @staticmethod
    def deserialize(data: bytes):
        return AudioPacket(data)