import logging
from datetime import datetime as dt
from time import time
from typing import List, Optional, Dict, Tuple
from uuid import uuid4 as uuid

import arrow
from cassandra.cluster import PlainTextAuthProvider
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table
from cassandra.cqlengine.query import BatchQuery

from dinofw.db.rdbms.schemas import UserGroupStatsBase
from dinofw.db.storage.models import AttachmentModel
from dinofw.db.storage.models import MessageModel
from dinofw.db.storage.schemas import MessageBase
from dinofw.rest.models import AttachmentQuery
from dinofw.rest.models import CreateActionLogQuery
from dinofw.rest.models import CreateAttachmentQuery
from dinofw.rest.models import MessageQuery
from dinofw.rest.models import SendMessageQuery
from dinofw.utils.config import ConfigKeys, MessageTypes
from dinofw.utils.exceptions import NoSuchMessageException, NoSuchAttachmentException


class CassandraHandler:
    ACTION_TYPE_JOIN = 0
    ACTION_TYPE_LEAVE = 1

    def __init__(self, env):
        self.env = env
        self.logger = logging.getLogger(__name__)

        # used when no `hide_before` is specified in a query
        beginning_of_1995 = 789_000_000
        self.long_ago = dt.utcfromtimestamp(beginning_of_1995)

    def setup_tables(self):
        key_space = self.env.config.get(ConfigKeys.KEY_SPACE, domain=ConfigKeys.STORAGE)
        hosts = self.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.STORAGE)
        hosts = hosts.split(",")

        if ConfigKeys.PASSWORD in self.env.config.get(ConfigKeys.STORAGE):
            auth_provider = PlainTextAuthProvider(
                username=self.env.config.get(ConfigKeys.USER, domain=ConfigKeys.STORAGE),
                password=self.env.config.get(ConfigKeys.PASSWORD, domain=ConfigKeys.STORAGE),
            )
            connection.setup(
                hosts,
                default_keyspace=key_space,
                protocol_version=3,
                retry_connect=True,
                auth_provider=auth_provider,
            )
        else:
            connection.setup(
                hosts,
                default_keyspace=key_space,
                protocol_version=3,
                retry_connect=True,
            )

        sync_table(MessageModel)
        sync_table(AttachmentModel)

    def get_messages_in_group(
            self,
            group_id: str,
            query: MessageQuery
    ) -> List[MessageBase]:
        until = MessageQuery.to_dt(query.until)

        raw_messages = (
            MessageModel.objects(
                MessageModel.group_id == group_id,
                MessageModel.created_at <= until,
            )
            .limit(query.per_page or 100)
            .all()
        )

        messages = list()

        for message in raw_messages:
            messages.append(CassandraHandler.message_base_from_entity(message))

        return messages

    def get_attachments_in_group_for_user(
            self,
            group_id: str,
            user_stats: UserGroupStatsBase,
            query: MessageQuery
    ) -> List[MessageBase]:
        until = MessageQuery.to_dt(query.until)

        raw_attachments = (
            AttachmentModel.objects(
                AttachmentModel.group_id == group_id,
                AttachmentModel.created_at <= until,
                AttachmentModel.created_at > user_stats.delete_before,
            )
            .limit(query.per_page or 100)
            .all()
        )

        attachments = list()

        for attachment in raw_attachments:
            attachments.append(CassandraHandler.message_base_from_entity(attachment))

        return attachments

    def get_messages_in_group_for_user(
            self,
            group_id: str,
            user_stats: UserGroupStatsBase,
            query: MessageQuery
    ) -> List[MessageBase]:
        until = MessageQuery.to_dt(query.until)

        raw_messages = (
            MessageModel.objects(
                MessageModel.group_id == group_id,
                MessageModel.created_at < until,
                MessageModel.created_at > user_stats.delete_before,
            )
            .limit(query.per_page or 100)
            .all()
        )

        messages = list()

        for message in raw_messages:
            messages.append(CassandraHandler.message_base_from_entity(message))

        return messages

    def count_messages_in_group_since(self, group_id: str, since: dt) -> int:
        return (
            MessageModel.objects(
                MessageModel.group_id == group_id,
            )
            .filter(
                MessageModel.created_at > since,
            )
            .limit(None)
            .count()
        )

    def get_unread_in_group(self, group_id: str, user_id: int, last_read: dt) -> int:
        unread = self.env.cache.get_unread_in_group(group_id, user_id)
        if unread is not None:
            return unread

        unread = self.count_messages_in_group_since(group_id, last_read)

        self.env.cache.set_unread_in_group(group_id, user_id, unread)
        return unread

    def delete_attachments_in_all_groups(
        self,
        group_created_at: List[Tuple[str, dt]],
        user_id: int
    ) -> Dict[str, List[MessageBase]]:
        group_to_atts = dict()
        start = time()

        for group_id, created_at in group_created_at:
            attachments = self.delete_attachments(group_id, created_at, user_id)

            if len(attachments):
                group_to_atts[group_id] = attachments

        elapsed = time() - start
        if elapsed > 5:
            n = len(group_to_atts)
            self.logger.info(
                f"batch delete attachments in {n} groups for user {user_id} took {elapsed:.2f}s"
            )

        return group_to_atts

    def delete_attachments(
        self,
        group_id: str,
        group_created_at: dt,
        user_id: int
    ) -> List[MessageBase]:
        attachments = (
            AttachmentModel.objects(
                AttachmentModel.group_id == group_id,
                AttachmentModel.created_at > group_created_at,
                AttachmentModel.user_id == user_id,
            )
            .allow_filtering()
            .all()
        )

        file_ids = {attachment.file_id for attachment in attachments}
        attachment_msg_ids = {attachment.message_id for attachment in attachments}
        attachment_bases = [
            CassandraHandler.message_base_from_entity(attachment) for attachment in attachments
        ]

        # no un-deleted attachments in this group
        if not len(file_ids):
            return list()

        messages_all = (
            MessageModel.objects(
                MessageModel.group_id == group_id,
                MessageModel.created_at > group_created_at,
                MessageModel.user_id == user_id,
                MessageModel.message_type == MessageTypes.IMAGE,  # TODO: need to have type in query? image/video/etc.
            )
            .allow_filtering()
            .all()
        )
        messages = [
            message for message in messages_all
            if message.message_id in attachment_msg_ids
        ]

        self._delete_messages(messages, "messages")
        self._delete_messages(attachments, "attachments")

        return attachment_bases

    def delete_attachment(
        self,
        group_id: str,
        group_created_at: dt,
        query: AttachmentQuery
    ) -> MessageBase:
        attachment = (
            AttachmentModel.objects(
                AttachmentModel.group_id == group_id,
                AttachmentModel.created_at > group_created_at,
                AttachmentModel.file_id == query.file_id,
            )
            .allow_filtering()
            .first()
        )

        if attachment is None:
            raise NoSuchAttachmentException(query.file_id)

        # to be returned
        attachment_base = CassandraHandler.message_base_from_entity(attachment)

        # convert uuid to str
        message_id = str(attachment.message_id)

        self.delete_message(
            group_id,
            attachment.user_id,
            message_id,
            attachment.created_at
        )

        # delete attachment after message; delete_message() throws NoSuchMessage if not found
        attachment.delete()

        return attachment_base

    def delete_message(
        self, group_id: str, user_id: int, message_id: str, created_at: dt
    ) -> None:
        approx_date = arrow.get(created_at).shift(minutes=-1).datetime

        message = (
            MessageModel.objects(
                MessageModel.group_id == group_id,
                MessageModel.created_at > approx_date,
                MessageModel.user_id == user_id,
                MessageModel.message_id == message_id,
            )
            .allow_filtering()
            .first()
        )

        if message is None:
            raise NoSuchMessageException(message_id)

        removed_at = arrow.utcnow().datetime

        message.update(
            message_payload="",
            removed_at=removed_at,
            updated_at=removed_at,
        )

    def get_attachment_from_file_id(self, group_id: str, created_at: dt, query: AttachmentQuery) -> MessageBase:
        approx_date = arrow.get(created_at).shift(minutes=-1).datetime

        attachment = (
            AttachmentModel.objects(
                AttachmentModel.group_id == group_id,
                AttachmentModel.created_at > approx_date,
                AttachmentModel.file_id == query.file_id,
            )
            .allow_filtering()
            .first()
        )

        if attachment is None:
            raise NoSuchAttachmentException(query.file_id)

        return CassandraHandler.message_base_from_entity(attachment)

    def store_attachment(
            self, group_id: str, user_id: int, message_id: str, query: CreateAttachmentQuery
    ) -> MessageBase:
        # we should filter on the 'created_at' field, since it's a clustering key
        # and 'message_id' is not; if we don't filter by 'created_at' each edit
        # will require a full table scan, and editing a recent message happens
        # quite often, which will become very slow after a group has a long
        # message history...
        created_at = query.created_at
        now = arrow.utcnow().datetime

        # querying by exact datetime seems to be shifty in cassandra, so just
        # filter by a minute before and after
        approx_date_after = arrow.get(created_at).shift(minutes=-1).datetime
        approx_date_before = arrow.get(created_at).shift(minutes=1).datetime

        message = (
            MessageModel.objects(
                MessageModel.group_id == group_id,
                MessageModel.user_id == user_id,
                MessageModel.created_at > approx_date_after,
                MessageModel.created_at < approx_date_before,
                MessageModel.message_id == message_id,
            )
            .allow_filtering()
            .first()
        )

        if message is None:
            raise NoSuchMessageException(message_id)

        message.update(
            message_payload=query.message_payload,
            file_id=query.file_id,
            updated_at=now,
        )

        AttachmentModel.create(
            group_id=group_id,
            user_id=user_id,
            created_at=message.created_at,
            message_id=message_id,
            message_payload=query.message_payload,
            message_type=message.message_type,
            updated_at=now,
            file_id=query.file_id,
        )

        return CassandraHandler.message_base_from_entity(message)

    def delete_messages_in_group(self, group_id: str, query: MessageQuery) -> None:
        def callback(message: MessageModel):
            message.removed_at = removed_at
            message.removed_by_user = query.admin_id

        removed_at = arrow.utcnow().datetime

        self._update_all_messages_in_group(group_id=group_id, callback=callback)

    def create_action_logs(
            self,
            group_id: str,
            query: CreateActionLogQuery
    ) -> List[MessageBase]:
        logs = list()

        action_time = arrow.utcnow().datetime

        for user_id in query.user_ids:
            log = MessageModel.create(
                group_id=group_id,
                user_id=user_id,
                created_at=action_time,
                message_type=query.action_type,
                message_payload=query.payload,
                message_id=uuid(),
            )

            logs.append(CassandraHandler.message_base_from_entity(log))

        return logs

    def delete_messages_in_group_for_user(
        self, group_id: str, user_id: int, query: MessageQuery
    ) -> None:
        # TODO: copy messages to another table `messages_deleted` and then remove the rows for `messages`

        def callback(message: MessageModel):
            message.removed_at = removed_at
            message.removed_by_user = query.admin_id

        removed_at = arrow.utcnow().datetime

        self._update_all_messages_in_group(
            group_id=group_id, callback=callback, user_id=user_id,
        )

    def store_message(self, group_id: str, user_id: int, query: SendMessageQuery) -> MessageBase:
        created_at = arrow.utcnow().datetime
        message_id = uuid()

        message = MessageModel.create(
            group_id=group_id,
            user_id=user_id,
            created_at=created_at,
            message_id=message_id,
            message_payload=query.message_payload,
            message_type=query.message_type,
        )

        return CassandraHandler.message_base_from_entity(message)

    def _update_all_messages_in_group(
        self, group_id: str, callback: callable, user_id: int = None
    ):
        until = arrow.utcnow().datetime
        start = time()
        amount = 0

        while True:
            messages = self._get_batch_of_messages_in_group(
                group_id=group_id, until=until, user_id=user_id,
            )

            if not len(messages):
                elapsed = time() - start

                if elapsed > 5 or amount > 500:
                    self.logger.info(
                        f"finished batch updating {amount} messages in group {group_id} after {elapsed:.2f}s"
                    )
                break

            amount += len(messages)
            until = self._update_messages(messages, callback)

    def _delete_messages(self, messages, types: str) -> None:
        start = time()
        with BatchQuery() as b:
            for message in messages:
                message.batch(b).delete()

        elapsed = time() - start
        if elapsed > 1:
            self.logger.info(f"batch deleted {len(message)} {types} in {elapsed:.2f}s")

    def _update_messages(
        self, messages: List[MessageModel], callback: callable
    ) -> Optional[dt]:
        until = None

        with BatchQuery() as b:
            for message in messages:
                callback(message)
                message.batch(b).save()

                until = message.created_at

        return until

    def _get_batch_of_messages_in_group(
        self, group_id: str, until: dt, user_id: int = None
    ) -> List[MessageModel]:
        if user_id is None:
            return (
                MessageModel.objects(
                    MessageModel.group_id == group_id,
                    MessageModel.created_at < until,
                )
                .limit(500)
                .all()
            )
        else:
            return (
                MessageModel.objects(
                    MessageModel.group_id == group_id,
                    MessageModel.user_id == user_id,
                    MessageModel.created_at < until,
                )
                .limit(500)
                .all()
            )

    @staticmethod
    def message_base_from_entity(message: MessageModel) -> MessageBase:
        return MessageBase(
            group_id=str(message.group_id),
            created_at=message.created_at,
            user_id=message.user_id,
            message_id=str(message.message_id),
            message_payload=message.message_payload,
            message_type=message.message_type,
            updated_at=message.updated_at,
            file_id=message.file_id,
        )
