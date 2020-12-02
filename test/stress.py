import random
import time
import sys
import numpy as np
import traceback
from functools import wraps

import requests


N_RUNS = 100
BASE_URL = sys.argv[1]
USERS = list()
HEADERS = {
    "Content-Type": "application/json"
}

with open("users.txt", "r") as f:
    for line in f:
        USERS.append(int(float(line.replace("\n", ""))))


class ApiKeys:
    GROUPS = "groups"
    HISTORIES = "histories"
    SEND = "send"


ALL_API_KEYS = [ApiKeys.__dict__[key] for key in ApiKeys.__dict__ if key.isupper()]


t_calls = {
    ApiKeys.GROUPS: list(),
    ApiKeys.HISTORIES: list(),
    ApiKeys.SEND: list(),
}
n_groups = 0
n_messages = 0


class Endpoints:
    BASE = "http://{host}/v1"

    GROUPS = BASE + "/users/{user_id}/groups"
    HISTORIES = BASE + "/groups/{group_id}/user/{user_id}/histories"
    SEND = BASE + "/users/{user_id}/send"


def timeit(key: str):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            before = time.time()

            try:
                return view_func(*args, **kwargs)
            finally:
                the_time = (time.time() - before) * 1000
                t_calls[key].append(the_time)
        return decorator
    return factory


@timeit(ApiKeys.GROUPS)
def call_groups(_user_id):
    r = requests.post(
        url=Endpoints.GROUPS.format(
            host=BASE_URL,
            user_id=_user_id
        ),
        json={
            "only_unread": False,
            "per_page": 50,
        },
        headers=HEADERS
    ).json()

    global n_groups
    n_groups += len(r)

    return r


@timeit(ApiKeys.HISTORIES)
def call_histories(_group_id, _user_id):
    r = requests.post(
        url=Endpoints.HISTORIES.format(
            host=BASE_URL,
            group_id=_group_id,
            user_id=_user_id
        ),
        json={
            "only_unread": False,
            "per_page": 50,
        },
        headers=HEADERS
    ).json()

    global n_messages
    n_messages += len(r["messages"])


@timeit(ApiKeys.SEND)
def call_send(_user_id, _receiver_id):
    requests.post(
        url=Endpoints.SEND.format(
            host=BASE_URL,
            user_id=_user_id
        ),
        json={
            "receiver_id": _receiver_id,
            "message_type": 0,
            "message_payload": "{\"content\":\"stress test message\"}"
        },
        headers=HEADERS
    )


def format_times(elapsed):
    print(f"time elapsed: {elapsed}")

    for key in ALL_API_KEYS:
        if not len(t_calls[key]):
            continue

        calls = t_calls[key]

        mean = np.mean(calls)
        median = np.median(calls)
        p95 = np.percentile(calls, 95)
        p99 = np.percentile(calls, 99)

        print(f"{key}: {len(calls)}, mean {mean:.2f}ms, median {median:.2f}, 95%: {p95:.2f}ms, 99%: {p99:.2f}ms")

    print(f"number of groups: {n_groups}")
    print(f"number of messages: {n_messages}")


test_start = time.time()

for _ in range(N_RUNS):
    try:
        user = random.choice(USERS)
        groups = call_groups(user)

        if len(groups) and "detail" not in groups:
            for _ in range(max(5, min(5, len(groups)))):
                group = random.choice(groups)
                call_histories(group["group"]["group_id"], user)

                users = [user["user_id"] for user in group["group"]["users"]]
                receiver_ids = [int(a_user) for a_user in users if int(a_user) != user]
                if not len(receiver_ids):
                    continue

                receiver_id = receiver_ids[0]
                call_send(user, receiver_id)

    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        time.sleep(2)
    except KeyboardInterrupt:
        break

test_elapsed = time.time() - test_start
format_times(test_elapsed)