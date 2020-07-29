from datetime import datetime as dt

import arrow
import pytz

from dinofw.rest.server.models import UpdateUserGroupStats, AbstractQuery
from test.base import BaseTest
from test.db_base import BaseDatabaseTest


class TestServerRestApi(BaseDatabaseTest):
    def test_get_groups_for_user_before_joining(self):
        self.assert_groups_for_user(0)

    def test_get_groups_for_user_after_joining(self):
        self.create_and_join_group()
        self.assert_groups_for_user(1)

    def test_leaving_a_group(self):
        self.assert_groups_for_user(0)

        group_id = self.create_and_join_group()
        self.assert_groups_for_user(1)

        self.user_leaves_group(group_id)
        self.assert_groups_for_user(0)

    def test_another_user_joins_group(self):
        self.assert_groups_for_user(0, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(0, user_id=BaseTest.OTHER_USER_ID)

        # first user joins, check that other user isn't in any groups
        group_id = self.create_and_join_group()
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(0, user_id=BaseTest.OTHER_USER_ID)

        # other user also joins, check that both are in a group now
        self.user_joins_group(group_id, user_id=BaseTest.OTHER_USER_ID)
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(1, user_id=BaseTest.OTHER_USER_ID)

    def test_users_in_group(self):
        self.assert_groups_for_user(0, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(0, user_id=BaseTest.OTHER_USER_ID)

        # first user joins, check that other user isn't in any groups
        group_id = self.create_and_join_group()
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(0, user_id=BaseTest.OTHER_USER_ID)

        # other user also joins, check that both are in a group now
        self.user_joins_group(group_id, user_id=BaseTest.OTHER_USER_ID)
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(1, user_id=BaseTest.OTHER_USER_ID)

    def test_update_user_statistics_in_group(self):
        group_id = self.create_and_join_group()

        now_ts = self.update_user_stats_to_now(group_id, BaseTest.USER_ID)
        user_stats = self.get_user_stats(group_id, BaseTest.USER_ID)

        self.assertEqual(group_id, user_stats["group_id"])
        self.assertEqual(BaseTest.USER_ID, user_stats["user_id"])
        self.assertEqual(now_ts, user_stats["last_read_time"])

    def test_group_unhidden_on_new_message_for_all_users(self):
        # both users join a new group
        group_id = self.create_and_join_group(BaseTest.USER_ID)
        self.user_joins_group(group_id, BaseTest.OTHER_USER_ID)

        # the group should not be hidden for either user at this time
        self.assert_hidden_for_user(False, group_id, BaseTest.USER_ID)
        self.assert_hidden_for_user(False, group_id, BaseTest.OTHER_USER_ID)

        # both users should have the group in the list
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(1, user_id=BaseTest.OTHER_USER_ID)

        # hide the group for the other user
        self.update_hide_group_for(group_id, True, BaseTest.OTHER_USER_ID)

        # make sure the group is hidden for the other user
        self.assert_hidden_for_user(False, group_id, BaseTest.USER_ID)
        self.assert_hidden_for_user(True, group_id, BaseTest.OTHER_USER_ID)

        # other user doesn't have any groups since he hid it
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(0, user_id=BaseTest.OTHER_USER_ID)

        # sending a message should un-hide the group for all users in it
        self.send_message_to_group_from(group_id, BaseTest.USER_ID)

        # should not be hidden anymore for any user
        self.assert_hidden_for_user(False, group_id, BaseTest.USER_ID)
        self.assert_hidden_for_user(False, group_id, BaseTest.OTHER_USER_ID)

        # both users have 1 group now since none is hidden anymore
        self.assert_groups_for_user(1, user_id=BaseTest.USER_ID)
        self.assert_groups_for_user(1, user_id=BaseTest.OTHER_USER_ID)

    def send_message_to_group_from(self, group_id: str, user_id: int = None):
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.post(
            f"/v1/groups/{group_id}/users/{user_id}/send",
            json={
                "message_payload": "test message",
                "message_type": "text",
            },
        )
        self.assertEqual(raw_response.status_code, 200)

    def update_hide_group_for(self, group_id: str, hide: bool, user_id: int = None):
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.put(
            f"/v1/groups/{group_id}/userstats/{user_id}",
            json={"hide": hide},
        )
        self.assertEqual(raw_response.status_code, 200)

    def update_user_stats_to_now(self, group_id: str, user_id: int = None):
        if user_id is None:
            user_id = BaseTest.USER_ID

        now = arrow.utcnow().datetime
        now_ts = AbstractQuery.to_ts(now)

        raw_response = self.client.put(
            f"/v1/groups/{group_id}/userstats/{user_id}",
            json={"last_read_time": now_ts},
        )
        self.assertEqual(raw_response.status_code, 200)

        return float(now_ts)

    def get_user_stats(self, group_id: str, user_id: int = None):
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.get(f"/v1/groups/{group_id}/userstats/{user_id}")
        self.assertEqual(raw_response.status_code, 200)

        return raw_response.json()

    def assert_hidden_for_user(self, hidden: bool, group_id: str, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.get(
            f"/v1/groups/{group_id}/userstats/{user_id}",
        )
        self.assertEqual(raw_response.status_code, 200)
        self.assertEqual(hidden, raw_response.json()["hide"])

    def assert_groups_for_user(self, amount_of_groups, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.post(
            f"/v1/users/{user_id}/groups", json={"per_page": "10"},
        )
        self.assertEqual(raw_response.status_code, 200)
        self.assertEqual(amount_of_groups, len(raw_response.json()))

    def create_and_join_group(self, user_id: int = None) -> str:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.post(
            f"/v1/users/{user_id}/groups/create",
            json={
                "group_name": "a new group",
                "group_type": 0,
                "users": [user_id],
            },
        )
        self.assertEqual(raw_response.status_code, 200)

        return raw_response.json()["group_id"]

    def user_leaves_group(self, group_id: str, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.delete(f"/v1/groups/{group_id}/users/{user_id}/join")
        self.assertEqual(raw_response.status_code, 200)

    def user_joins_group(self, group_id: str, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.put(f"/v1/groups/{group_id}/users/{user_id}/join")
        self.assertEqual(raw_response.status_code, 200)
