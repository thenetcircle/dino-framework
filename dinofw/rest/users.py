import logging
import random
from datetime import datetime
from typing import List

import pytz

from dinofw.rest.base import BaseResource
from dinofw.rest.models import Group
from dinofw.rest.models import GroupQuery
from dinofw.rest.models import UserStats

logger = logging.getLogger(__name__)


class UserResource(BaseResource):
    def __init__(self, env):
        self.env = env

    async def get_groups_for_user(self, user_id: int, query: GroupQuery, db) -> List[Group]:
        groups_stats_and_users = self.env.db.get_groups_for_user(user_id, query, db)
        groups = list()

        for group, user_group_stats, users in groups_stats_and_users:
            group_dict = group.dict()

            group_dict["users"] = users
            group_dict["last_read"] = GroupQuery.to_ts(user_group_stats.last_read)

            group_dict["created_at"] = GroupQuery.to_ts(group_dict["created_at"])
            group_dict["updated_at"] = GroupQuery.to_ts(group_dict["updated_at"])
            group_dict["last_message_time"] = GroupQuery.to_ts(group_dict["last_message_time"])

            groups.append(Group(**group_dict))

        return groups

    async def get_user_stats(self, user_id: int) -> UserStats:
        # TODO: groups = await self.get_groups_for_user()
        # TODO: get number of groups with unread messages in

        amount = int(random.random() * 10000)
        now = datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        now = float(now.strftime("%s.%f"))

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
            last_group_join_sent_time=now,
        )
