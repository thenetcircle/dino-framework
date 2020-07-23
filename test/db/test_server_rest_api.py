from test.base import BaseTest
from test.db import BaseDatabaseTest


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

    def assert_groups_for_user(self, amount_of_groups, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.post(
            f"/v1/users/{user_id}/groups",
            json={"per_page": "10"},
        )
        self.assertEqual(raw_response.status_code, 200)
        self.assertEqual(amount_of_groups, len(raw_response.json()))

    def create_and_join_group(self) -> str:
        raw_response = self.client.post(
            f"/v1/users/{BaseTest.USER_ID}/groups/create",
            json={
                "group_name": "a new group",
                "group_type": 0,
                "users": [BaseTest.USER_ID],
            },
        )
        self.assertEqual(raw_response.status_code, 200)
        return raw_response.json()["group_id"]

    def user_leaves_group(self, group_id: str, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.delete(
            f"/v1/groups/{group_id}/users/{user_id}/join"
        )
        self.assertEqual(raw_response.status_code, 200)

    def user_joins_group(self, group_id: str, user_id: int = None) -> None:
        if user_id is None:
            user_id = BaseTest.USER_ID

        raw_response = self.client.put(
            f"/v1/groups/{group_id}/users/{user_id}/join"
        )
        self.assertEqual(raw_response.status_code, 200)
