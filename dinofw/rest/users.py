import logging
import random
from datetime import datetime
import pytz
from typing import List

from dinofw.rest.base import BaseResource
from dinofw.rest.models import PaginationQuery
from dinofw.rest.models import GroupUsers
from dinofw.rest.models import UserStats
from dinofw.rest.models import Group

logger = logging.getLogger(__name__)


class UserResource(BaseResource):
    async def users(self, group_id: str, query: PaginationQuery) -> GroupUsers:
        return GroupUsers(
            owner_id=1,
            users=[1, 2, 3, 4]
        )

    async def stats(self, user_id: int) -> UserStats:
        amount = int(random.random() * 10000)
        now = datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        now = int(float(now.strftime("%s")))

        return UserStats(
            user_id=user_id,
            message_amount=amount,
            unread_amount=amount - int(random.random() * amount),
            group_amount=1 + random.random() * 20,
            owned_group_amount=1 + random.random() * 10,
            last_read_time=now,
            last_read_group_id=1,
            last_send_time=now,
            last_send_group_id=1,
            last_group_join_time=now,
            last_group_join_sent_time=now
        )

    async def groups(self, user_id: int) -> List[Group]:
        return [self._group()]