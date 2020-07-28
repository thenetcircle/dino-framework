from datetime import datetime as dt
from typing import Dict, List, Optional, Tuple
from uuid import uuid4 as uuid

import pytz

from dinofw.db.cassandra.schemas import MessageBase, ActionLogBase
from dinofw.db.rdbms.schemas import GroupBase
from dinofw.db.rdbms.schemas import UserGroupStatsBase
from dinofw.rest.server.models import (
    CreateGroupQuery,
    MessageQuery,
    EditMessageQuery,
    AbstractQuery,
)
from dinofw.rest.server.models import GroupQuery
from dinofw.rest.server.models import SendMessageQuery


class FakeStorage:
    ACTION_TYPE_JOIN = 0
    ACTION_TYPE_LEAVE = 1

    def __init__(self):
        self.messages_by_group = dict()
        self.action_log = dict()

    def store_message(
        self, group_id: str, user_id: int, query: SendMessageQuery
    ) -> MessageBase:
        if group_id not in self.messages_by_group:
            self.messages_by_group[group_id] = list()

        now = dt.utcnow()
        now = now.replace(tzinfo=pytz.UTC)

        message = MessageBase(
            group_id=group_id,
            created_at=now,
            user_id=user_id,
            message_id=str(uuid()),
            message_payload=query.message_payload,
            message_type=query.message_type,
        )

        self.messages_by_group[group_id].append(message)

        return message

    def create_join_action_log(
        self, group_id: str, users: Dict[int, float], action_time: dt
    ) -> List[ActionLogBase]:
        user_ids = [user_id for user_id, _ in users.items()]
        return self._create_action_log(
            group_id, user_ids, action_time, FakeStorage.ACTION_TYPE_JOIN
        )

    def create_leave_action_log(
        self, group_id: str, user_ids: [int], action_time: dt
    ) -> List[ActionLogBase]:
        return self._create_action_log(
            group_id, user_ids, action_time, FakeStorage.ACTION_TYPE_LEAVE
        )

    def _create_action_log(
        self, group_id: str, user_ids: List[int], action_time: dt, action_type: int
    ) -> List[ActionLogBase]:
        if group_id not in self.action_log:
            self.action_log[group_id] = list()

        new_logs = list()

        for user_id in user_ids:
            log = ActionLogBase(
                group_id=group_id,
                user_id=user_id,
                created_at=action_time,
                action_type=action_type,
                action_id=str(uuid()),
            )

            new_logs.append(log)
            self.action_log[group_id].append(log)

        return new_logs

    def get_messages_in_group(
        self, group_id: str, query: MessageQuery
    ) -> List[MessageBase]:
        if group_id not in self.messages_by_group:
            return list()

        messages = list()

        for message in self.messages_by_group[group_id]:
            messages.append(message)

            if len(messages) > query.per_page:
                break

        return messages

    def get_messages_in_group_for_user(
        self, group_id: str, user_id: int, query: MessageQuery
    ) -> List[MessageBase]:
        if group_id not in self.messages_by_group:
            return list()

        messages = list()

        for message in self.messages_by_group[group_id]:
            if message.user_id == user_id:
                messages.append(message)

            if len(messages) > query.per_page:
                break

        return messages

    def edit_message(
        self, group_id: str, user_id: int, message_id: str, query: EditMessageQuery
    ) -> Optional[MessageBase]:

        message = None

        for m in self.messages_by_group[group_id]:
            if m.message_id == message_id:
                message = m
                break

        if message is None:
            return None

        if query.message_payload is not None:
            message.message_payload = query.message_payload
        if query.message_type is not None:
            message.message_type = query.message_type
        if query.status is not None:
            message.status = query.status

        now = dt.utcnow()
        now = now.replace(tzinfo=pytz.UTC)

        message.updated_at = now

        return message

    def get_action_log_in_group(
        self, group_id: str, query: MessageQuery
    ) -> List[ActionLogBase]:
        logs = list()

        if group_id not in self.action_log:
            return list()

        for log in self.action_log[group_id]:
            logs.append(log)

            if len(logs) > query.per_page:
                break

        return logs

    def count_messages_in_group(self, group_id: str) -> int:
        if group_id not in self.messages_by_group:
            return 0

        return len(self.messages_by_group[group_id])

    def count_messages_in_group_since(self, group_id: str, since: dt) -> int:
        if group_id not in self.messages_by_group:
            return 0

        messages = list()

        for message in self.messages_by_group[group_id]:
            if message.created_at < since:
                continue

            messages.append(message)

        return len(messages)


class FakeDatabase:
    def __init__(self):
        self.groups = dict()
        self.stats = dict()

    def update_group_new_message(self, message: MessageBase, sent_time: dt, _) -> None:
        if message.group_id not in self.groups:
            return

        self.groups[message.group_id].last_message_time = sent_time
        self.groups[message.group_id].last_message_overview = message.message_payload

    def create_group(self, owner_id: int, query: CreateGroupQuery, _) -> GroupBase:
        created_at = dt.utcnow()
        created_at = created_at.replace(tzinfo=pytz.UTC)

        group = GroupBase(
            group_id=str(uuid()),
            name=query.group_name,
            group_type=query.group_type,
            last_message_time=created_at,
            created_at=created_at,
            owner_id=owner_id,
            group_meta=query.group_meta,
            group_context=query.group_context,
            description=query.description,
        )

        self.groups[group.group_id] = group

        return group

    def get_groups_for_user(
        self, user_id: int, query: GroupQuery, _, count_users: bool = True
    ) -> List[Tuple[GroupBase, UserGroupStatsBase, Dict[int, float], int]]:
        groups = list()
        sub_query = GroupQuery(per_page=50)

        if user_id not in self.stats:
            return list()

        for stat in self.stats[user_id]:
            users = self.get_user_ids_and_join_times_in_group(
                stat.group_id, sub_query, None
            )

            if count_users:
                user_count = self.count_users_in_group(stat.group_id, None)
            else:
                user_count = 0

            group = self.groups[stat.group_id]
            groups.append((group, stat, users, user_count))

            if len(groups) > query.per_page:
                break

        return groups

    def get_users_in_group(
        self, group_id: str, query: GroupQuery, db
    ) -> (Optional[GroupBase], Optional[Dict[int, float]], Optional[int]):
        if group_id not in self.groups:
            return None, None, None

        group = self.groups[group_id]
        users = self.get_user_ids_and_join_times_in_group(group_id, query, db)
        user_count = self.count_users_in_group(group_id, db)

        return group, users, user_count

    def count_users_in_group(self, group_id: str, _) -> int:
        users = list()

        for user_id, stats in self.stats.items():
            for stat in stats:
                if stat.group_id == group_id:
                    users.append(user_id)

        return len(users)

    def update_last_read_and_sent_in_group_for_user(
        self, user_id: int, group_id: str, created_at: dt, _
    ) -> None:
        if user_id in self.stats:
            for group_stats in self.stats[user_id]:
                if group_stats.group_id == group_id:
                    group_stats.last_read = created_at
                    group_stats.last_sent = created_at
        else:
            self.stats[user_id] = [
                UserGroupStatsBase(
                    group_id=group_id,
                    user_id=user_id,
                    last_read=created_at,
                    last_sent=created_at,
                    hide_before=created_at,
                    join_time=created_at,
                )
            ]

    def update_last_read_in_group_for_user(
        self, group_id: str, users: Dict[int, float], last_read_time: dt, _
    ) -> None:

        for user_id, join_time in users.items():
            base_to_add = UserGroupStatsBase(
                group_id=group_id,
                user_id=user_id,
                last_read=last_read_time,
                hide_before=last_read_time,
                last_sent=last_read_time,
                join_time=join_time,
            )

            if user_id not in self.stats:
                self.stats[user_id] = [base_to_add]

            else:
                found_existing = False

                for group_stats in self.stats[user_id]:
                    if group_stats.group_id == group_id:
                        found_existing = True
                        group_stats.last_read = last_read_time

                if not found_existing:
                    self.stats[user_id].append(base_to_add)

    def remove_last_read_in_group_for_user(
        self, group_id: str, user_id: int, _
    ) -> None:
        if user_id not in self.stats:
            return

        old_stats = self.stats[user_id]
        new_stats = list()

        for old_stat in old_stats:
            if old_stat.group_id == group_id:
                continue

            new_stats.append(old_stat)

        self.stats[user_id] = new_stats

    def group_exists(self, group_id: str, _) -> bool:
        return group_id in self.groups

    def get_user_ids_and_join_times_in_group(
        self, group_id: str, query: GroupQuery, _, skip_cache: bool = False
    ) -> Dict[int, float]:
        response = dict()

        for _, stats in self.stats.items():
            for stat in stats:
                if stat.group_id == group_id:
                    response[stat.user_id] = AbstractQuery.to_ts(stat.join_time)
                    break

            if len(response) > query.per_page:
                break

        return response  # noqa

    def get_user_stats_in_group(
        self, group_id: str, user_id: int, _
    ) -> Optional[UserGroupStatsBase]:
        if user_id not in self.stats:
            return None

        for stat in self.stats[user_id]:
            if stat.group_id == group_id:
                return stat

        return None


class FakePublisher:
    def __init__(self):
        self.sent_messages = dict()

    def message(self, group_id, user_id, message, user_ids):
        if group_id not in self.sent_messages:
            self.sent_messages[group_id] = list()

        self.sent_messages[group_id].append(message)


class FakeCache:
    def set_user_ids_and_join_time_in_group(self, group_id, users):
        return

    def get_user_ids_and_join_time_in_group(self, _):
        return None

    def get_user_count_in_group(self, _):
        return None

    def set_user_stats_group(self, group_id, user_id, _):
        pass

    def get_user_stats_group(self, group_id, user_id):
        return None


class FakeEnv:
    class Config:
        def __init__(self):
            self.config = {
                "storage": {
                    "key_space": "dinofw",
                    "host": "maggie-cassandra-1,maggie-cassandra-2",
                }
            }

        def get(self, key, domain):
            return self.config[domain][key]

    def __init__(self):
        self.config = FakeEnv.Config()
        self.storage = FakeStorage()
        self.db = FakeDatabase()
        self.publisher = FakePublisher()
        self.cache = FakeCache()

        from dinofw.rest.server.groups import GroupResource
        from dinofw.rest.server.users import UserResource
        from dinofw.rest.server.message import MessageResource

        class RestResources:
            group: GroupResource
            user: UserResource
            message: MessageResource

        self.rest = RestResources()
        self.rest.group = GroupResource(self)
        self.rest.user = UserResource(self)
        self.rest.message = MessageResource(self)