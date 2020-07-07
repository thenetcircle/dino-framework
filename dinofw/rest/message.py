import logging
from typing import List

from sqlalchemy.orm import Session

from dinofw.rest.base import BaseResource
from dinofw.rest.models import (
    SendMessageQuery,
    HistoryQuery,
    Message,
    EditMessageQuery,
    AdminQuery,
    MessageQuery,
)

logger = logging.getLogger(__name__)


class MessageResource(BaseResource):
    def __init__(self, env):
        self.env = env

    async def save_new_message(self, group_id: str, user_id: int, query: SendMessageQuery, db: Session) -> Message:
        message = self.env.storage.store_message(group_id, user_id, query)

        self.env.db.update_group_new_message(message, db)
        self.env.db.update_last_read_on_send_new_message(user_id, message, db)

        message_dict = message.dict()

        message_dict["removed_at"] = MessageQuery.to_ts(message_dict["removed_at"])
        message_dict["updated_at"] = MessageQuery.to_ts(message_dict["updated_at"])
        message_dict["created_at"] = MessageQuery.to_ts(message_dict["created_at"])

        return Message(**message_dict)

    async def edit(self, group_id: str, user_id: int, query: EditMessageQuery) -> None:
        pass

    async def delete(self, group_id: str, user_id: int, query: AdminQuery) -> None:
        pass

    async def details(self, group_id: str, user_id: int, message_id: str) -> Message:
        pass

    async def messages_in_group(self, group_id: str, query: MessageQuery) -> List[Message]:
        raw_messages = self.env.storage.get_messages_in_group(group_id, query)
        messages = list()

        for message in raw_messages:
            message_dict = message.dict()

            message_dict["removed_at"] = MessageQuery.to_ts(message_dict["removed_at"])
            message_dict["updated_at"] = MessageQuery.to_ts(message_dict["updated_at"])
            message_dict["created_at"] = MessageQuery.to_ts(message_dict["created_at"])

            messages.append(Message(**message_dict))

        return messages

    async def messages_for_user(
        self, group_id: str, user_id: int, query: HistoryQuery
    ) -> List[Message]:
        return [self._message(group_id, user_id)]

    async def update_messages_for_user(
        self, group_id: str, user_id: int, query: MessageQuery
    ) -> List[Message]:
        pass

    async def delete_messages_for_user_in_group(
        self, group_id: str, user_id: int, query: AdminQuery
    ):
        pass

    async def update_messages(self, group_id: str, query: HistoryQuery):
        pass

    async def delete_messages(self, group_id: str, query: HistoryQuery):
        pass
