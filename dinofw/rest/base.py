import random
from abc import ABC
from datetime import datetime
from uuid import uuid4 as uuid

import pytz

from dinofw.rest.models import Group, Message, Joiner


class BaseResource(ABC):
    def _group(self, group_id=None):
        now = datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        now = float(now.strftime("%s.%f"))

        if group_id is None:
            group_id = str(uuid())

        return Group(
            group_id=group_id,
            name="a group name",
            description="some description",
            status=0,
            group_type=0,
            created_at=now,
            updated_at=now,
            owner_id=0,
            group_meta=0,
            group_context="",
            last_message_overview="some text",
            last_message_user_id=0,
            last_message_time=now,
        )

    def _join(self, group_id, status=None):
        now = datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        now = float(now.strftime("%s.%f"))

        if status is None:
            status = 0

        return Joiner(
            joined_id=int(random.random() * 1000000),
            group_id=group_id,
            inviter_id=int(random.random() * 1000000),
            created_at=now,
            status=status,
            invitation_context="",
        )

    def _message(self, group_id, user_id=None, message_id=None):
        now = datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        now = float(now.strftime("%s.%f"))

        if user_id is None:
            user_id = int(random.random() * 1000000)

        if message_id is None:
            message_id = str(uuid())

        return Message(
            message_id=message_id,
            group_id=group_id,
            user_id=user_id,
            created_at=now,
            status=0,
            message_type=0,
            read_at=now,
            updated_at=now,
            last_action_log_id=0,
            removed_at=now,
            removed_by_user=0,
            message_payload="some message payload",
        )
