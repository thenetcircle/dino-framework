from abc import ABC, abstractmethod
from typing import List

from dinofw.db.rdbms.schemas import GroupBase
from dinofw.db.storage.schemas import MessageBase, AttachmentBase
from dinofw.rest.models import AbstractQuery


class IPublishHandler(ABC):
    @abstractmethod
    def message(self, message: MessageBase, attachments: List[AttachmentBase], user_ids: List[int]) -> None:
        """pass"""

    @abstractmethod
    def attachment(self, attachment: AttachmentBase, user_ids: List[int]) -> None:
        """pass"""

    @abstractmethod
    def group_change(self, group_base: GroupBase, user_ids: List[int]) -> None:
        """pass"""

    @abstractmethod
    def join(self, group_id: str, user_ids: List[int], joiner_id: int, now: float) -> None:
        """pass"""

    @abstractmethod
    def leave(self, group_id: str, user_ids: List[int], leaver_id: int, now: float) -> None:
        """pass"""

    @staticmethod
    def create_simple_event(event_type: str, group_id: str, user_id: int, now: float) -> dict:
        return {
            "event_type": event_type,
            "created_at": now,
            "group_id": group_id,
            "user_id": user_id,
        }

    @staticmethod
    def message_base_to_event(message: MessageBase, attachments: List[AttachmentBase]):
        attachments = [{
            "attachment_id": attachment.attachment_id,
            "is_resized": attachment.is_resized,
            "context": attachment.context,
            "created_at": AbstractQuery.to_ts(attachment.created_at, allow_none=True) or "",
            "updated_at": AbstractQuery.to_ts(attachment.updated_at, allow_none=True) or "",
        } for attachment in attachments]

        return {
            "event_type": "message",
            "group_id": message.group_id,
            "sender_id": message.user_id,
            "message_id": message.message_id,
            "message_payload": message.message_payload,
            "message_type": message.message_type,
            "status": message.status,
            "updated_at": AbstractQuery.to_ts(message.updated_at, allow_none=True) or "",
            "created_at": AbstractQuery.to_ts(message.created_at),
            "attachments": attachments
        }

    @staticmethod
    def attachment_base_to_event(attachment: AttachmentBase):
        return {
            "event_type": "attachment",
            "attachment_id": attachment.attachment_id,
            "message_id": attachment.message_id,
            "group_id": attachment.group_id,
            "sender_id": attachment.user_id,
            "is_resized": attachment.is_resized,
            "updated_at": AbstractQuery.to_ts(attachment.updated_at, allow_none=True) or "",
            "created_at": AbstractQuery.to_ts(attachment.created_at),
            "context": attachment.context,
            "filename": attachment.filename,
        }

    @staticmethod
    def group_base_to_event(group: GroupBase, user_ids: List[int]):
        return {
            "event_type": "group",
            "group_id": group.group_id,
            "name": group.name,
            "description": group.description,
            "created_at": AbstractQuery.to_ts(group.created_at),
            "updated_at": AbstractQuery.to_ts(group.updated_at, allow_none=True) or None,
            "last_message_time": AbstractQuery.to_ts(group.last_message_time, allow_none=True) or None,
            "last_message_overview": group.last_message_overview,
            "last_message_type": group.last_message_type,
            "last_message_user_id": group.last_message_user_id,
            "status": group.status,
            "group_type": group.group_type,
            "owner_id": group.owner_id,
            "meta": group.meta,
            "weight": group.weight,
            "context": group.context,
            "user_ids": ",".join([str(user_id) for user_id in user_ids]),
        }


class IPublisher(ABC):
    @abstractmethod
    def send(self, user_id: int, fields: dict) -> None:
        """
        publish a bunch of fields to the configured stream
        """
