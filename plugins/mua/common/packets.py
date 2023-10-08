import json
from typing import Dict, Any


class Packet:
    TYPE = None

    def __init__(self):
        pass

    def serialize_content(self) -> Dict[str, Any]:
        pass

    def __str__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        content = self.serialize_content()
        return json.dumps({"type": self.TYPE, "content": content}, ensure_ascii=False)

    @staticmethod
    def from_json(src):
        obj = json.loads(src)
        packet_type = REGISTRY[obj["type"]]
        return packet_type.from_json_content(obj["content"])

    @staticmethod
    def from_json_content():
        raise NotImplementedError()


class ClientAuthPacket(Packet):
    TYPE = "CLIENT_AUTH"

    AUTH_DEFAULT = "UNION"

    def __init__(self, auth_type, auth_field):
        self.auth_type = auth_type
        self.auth_field = auth_field

    @classmethod
    def default_auth_type(cls, id, token):
        return cls(cls.AUTH_DEFAULT, {"id": id, "token": token})

    def serialize_content(self):
        return {"type": self.auth_type, "field": self.auth_field}

    @classmethod
    def from_json_content(cls, content: dict):
        return cls(content["type"], content["field"])


class AuthSuccessPacket(Packet):
    TYPE = "AUTH_SUCCESS"

    def __init__(self, id):
        self.id = id

    def serialize_content(self):
        return {}

    @classmethod
    def from_json_content(cls, content: dict):
        return cls(content["id"])

    def serialize_content(self):
        return {"id": self.id}


class ErrorPacket(Packet):
    TYPE = "ERROR"

    E_AUTH_FAILURE = "AUTH_FAILURE"
    E_UNKNOWN_TARGET = "UNKNOWN_TARGET"

    def __init__(self, error_code, error_info=None):
        self.error_code = error_code
        self.error_info = error_info

    def to_json(self):
        self.content = {"code": self.error_code, "info": self.error_info}

    @classmethod
    def from_json_content(cls, content: dict):
        return cls(content["code"], content.get("info", None))


class PayloadPacket(Packet):
    TYPE = "PAYLOAD"
    SUBPROTOCOL_TYPE = None

    __SUBPROTOCOL_REGISTRY = {}

    def __init__(self,
                 subprotocol_name: str,
                 subprotocol_version: int,
                 subprotocol_packet_type: str,
                 body: str = None,
                 targets: list = None,
                 sender: str = None,
                 session_id=None):
        self.subprotocol_name: str = subprotocol_name
        self.subprotocol_version: int = subprotocol_version
        self.subprotocol_packet_type: str = subprotocol_packet_type
        self.targets: list = targets
        self.body: str = body
        self.sender: str = sender
        self.session_id = session_id

    def get_json_body(self) -> str:
        return self.body

    def get_subprotocol_name(self) -> str:
        return self.subprotocol_name

    def get_subprotocol_version(self) -> int:
        return self.subprotocol_version

    def get_subprotocol_packet_type(self) -> str:
        return self.subprotocol_packet_type

    def serialize_content(self) -> Dict[str, Any]:
        content = {
            "subprotocol": {
                "name": self.subprotocol_name,
                "version": self.subprotocol_version,
                "packet_type": self.subprotocol_packet_type
            },
            "body": self.get_json_body(),
        }
        if self.targets is not None:
            content["targets"] = self.targets
        if self.session_id is not None:
            content["session_id"] = self.session_id
        return content

    def get_session_id(self):
        return self.session_id

    def set_session_id(self, session_id):
        self.session_id = session_id

    def set_body(self, body):
        self.body = body

    def set_target(self, target: list):
        self.targets = target

    @classmethod
    def from_payload_packet(cls, payload_packet):
        raise NotImplementedError

    @classmethod
    def from_json_content(cls, content: dict):
        return cls(
            content["subprotocol"]["name"],
            content["subprotocol"]["version"],
            content["subprotocol"]["packet_type"],
            body=content.get("body", None),
            targets=content.get("targets", None),
            session_id=content.get("session_id", None)
        )

    def as_subprotocol_packet(self):
        if self.subprotocol_name in self.__SUBPROTOCOL_REGISTRY and self.subprotocol_packet_type in \
                self.__SUBPROTOCOL_REGISTRY[self.subprotocol_name]:
            return self.__SUBPROTOCOL_REGISTRY[self.subprotocol_name][self.subprotocol_packet_type].from_payload_packet(
                self)
        return None

    @classmethod
    def register_subprotocol(cls, subprotocol_name, subprotocol_registry):
        cls.__SUBPROTOCOL_REGISTRY[subprotocol_name] = subprotocol_registry


REGISTRY = {
    ClientAuthPacket.TYPE: ClientAuthPacket,
    AuthSuccessPacket.TYPE: AuthSuccessPacket,
    ErrorPacket.TYPE: ErrorPacket,
    PayloadPacket.TYPE: PayloadPacket,
}
