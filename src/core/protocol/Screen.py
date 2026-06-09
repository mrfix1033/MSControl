from src.core.protocol.FromClient import FromClientPacket


class ScreenPacket(FromClientPacket):
    def __init__(self, encoded_img: bytes):
        self.encoded_img = encoded_img

    @staticmethod
    def get_id() -> str:
        return __class__.__name__

    def serialize(self) -> bytes:
        return self.encoded_img

    @staticmethod
    def deserialize(data: bytes):
        return ScreenPacket(data)