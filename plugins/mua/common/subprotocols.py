from .packets import PayloadPacket
import time
import json
from typing import Union, Optional, List, Tuple, Set
# --------------------
#     ANNOUNCEMENT
# --------------------

SUBPROTOCOL_ANNOUNCEMENT_NAME = "ANNOUNCEMENT"
SUBPROTOCOL_ANNOUNCEMENT_VERSION = 1

class Announcement:
    def __init__(self, 
                title : str, 
                content,
                author_token : Optional[str],
                channel : str,
                tags : Union[List[str], Tuple[str], Set[str], None],
                targets : Union[List[str], Tuple[str], Set[str], None],
                time_created : int,
                time_expires : Optional[int],
                meta : dict = {}):
        self.title = title
        self.content = content
        self.author_token = author_token
        self.author_id = None
        self.channel = channel
        self.tags = tags
        self.targets = targets
        self.time_created = time_created
        self.time_expires = time_expires
        self.meta = meta

    def serialize(self, is_server=False):
        r = {
            "title" : self.title,
            "content" : self.content,
            "channel" : self.channel,
            "tags" : self.tags,
            "time_created" : self.time_created,
            "meta" : self.meta
        }
        if not is_server:
            r["author_token"] = self.author_token
        if self.author_id is not None:
            r["author_id"] = self.author_id
        if self.time_expires is not None:
            r["time_expires"] = self.time_expires
        if self.targets is not None:
            r["targets"] = self.targets
        return r
    
    @classmethod
    def from_json(cls, s):
        ret = cls(
            title=s["title"],
            content=s["content"],
            author_token=s.get("author_token", None),
            channel=s["channel"],
            tags=s["tags"],
            targets=s.get("targets", None),
            time_created=s["time_created"],
            time_expires=s.get("time_expires", None),
            meta=s["meta"]
        )
        ret.author_id = s.get("author_id", None)
        return ret

    def __hash__(self) -> int:
        return hash(self.title + self.content + self.channel)
    def __str__(self) -> str:
        return json.dumps(self.serialize(), ensure_ascii=False)
class CreateAnnouncementPacket(PayloadPacket):
    SUBPROTOCOL_TYPE = "CREATE"

    def __init__(self, announcement : Announcement, is_server=False, session_id=None):
        super().__init__(
            subprotocol_name = SUBPROTOCOL_ANNOUNCEMENT_NAME,
            subprotocol_version = SUBPROTOCOL_ANNOUNCEMENT_VERSION, 
            subprotocol_packet_type = self.SUBPROTOCOL_TYPE,
            session_id=session_id
        )
        self.announcement = announcement
        self.is_server = is_server

    def get_json_body(self):
        return self.announcement.serialize(self.is_server)

    @classmethod
    def from_payload_packet(cls, payload : PayloadPacket):
        return cls(
            Announcement.from_json(payload.body)
        )

class AnnouncementOperationResultPacket(PayloadPacket):
    SUBPROTOCOL_TYPE = "RESULT"

    def __init__(self, success : bool, aid : int, reason : str = None):
        super().__init__(
            subprotocol_name = SUBPROTOCOL_ANNOUNCEMENT_NAME,
            subprotocol_version = SUBPROTOCOL_ANNOUNCEMENT_VERSION, 
            subprotocol_packet_type = self.SUBPROTOCOL_TYPE,
        )
        self.success = success
        self.reason = reason
        self.aid = aid
        self.body = {
            "success" : success,
            "reason" : reason,
            "aid" : aid
        }

    @classmethod
    def from_payload_packet(cls, payload : PayloadPacket):
        return cls(
            payload.body["success"],
            payload.body.get("reason", None),
            payload.body["id"]
        )

class DeleteAnnouncementPacket(PayloadPacket):
    SUBPROTOCOL_TYPE = "DELETE"
    
    def __init__(self, aid : int, author_token : str):
        super().__init__(
            subprotocol_name = SUBPROTOCOL_ANNOUNCEMENT_NAME,
            subprotocol_version = SUBPROTOCOL_ANNOUNCEMENT_VERSION, 
            subprotocol_packet_type = self.SUBPROTOCOL_TYPE,
        )
        self.aid = aid
        self.author_token = author_token
        self.body = {
            "aid" : aid,
            "author_token" : author_token
        }

    @classmethod
    def from_payload_packet(cls, payload : PayloadPacket):
        return cls(payload.body["aid"], payload.body["author_token"])

class QueryAnnouncementListPacket(PayloadPacket):
    SUBPROTOCOL_TYPE = "QUERY"
    
    def __init__(self, session_id:str=None):
        super().__init__(
            subprotocol_name = SUBPROTOCOL_ANNOUNCEMENT_NAME,
            subprotocol_version = SUBPROTOCOL_ANNOUNCEMENT_VERSION, 
            subprotocol_packet_type = self.SUBPROTOCOL_TYPE,
            session_id=session_id,
        )

    @classmethod
    def from_payload_packet(cls, payload : PayloadPacket):
        return cls()

class AnnouncementListPacket(PayloadPacket):
    SUBPROTOCOL_TYPE = "LIST"
    
    def __init__(self, announcement_list : dict):
        super().__init__(
            subprotocol_name = SUBPROTOCOL_ANNOUNCEMENT_NAME,
            subprotocol_version = SUBPROTOCOL_ANNOUNCEMENT_VERSION, 
            subprotocol_packet_type = self.SUBPROTOCOL_TYPE,
        )
        self.announcement_list = announcement_list

    def get_json_body(self):
        body = {}
        for channel in self.announcement_list:
            body[channel] = []
            for announcement in self.announcement_list[channel]:
                body[channel].append(announcement)
        return body

    @classmethod
    def from_payload_packet(cls, payload : PayloadPacket):
        announcement_list = {}
        for channel in payload.body:
            announcement_list[channel] = []
            for announcement_json in payload.body[channel]:
                announcement_list[channel].append(Announcement.from_json(announcement_json))
        return cls(
            announcement_list
        )

SUBPROTOCOL_ANNOUNCEMENT_REGISTRY = {
    CreateAnnouncementPacket.SUBPROTOCOL_TYPE : CreateAnnouncementPacket,
    AnnouncementOperationResultPacket.SUBPROTOCOL_TYPE : AnnouncementOperationResultPacket,
    DeleteAnnouncementPacket.SUBPROTOCOL_TYPE : DeleteAnnouncementPacket,
    QueryAnnouncementListPacket.SUBPROTOCOL_TYPE : QueryAnnouncementListPacket,
    AnnouncementListPacket.SUBPROTOCOL_TYPE : AnnouncementListPacket,
}
PayloadPacket.register_subprotocol(SUBPROTOCOL_ANNOUNCEMENT_NAME, SUBPROTOCOL_ANNOUNCEMENT_REGISTRY)