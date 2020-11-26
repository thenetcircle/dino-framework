import random
import time
import sys
import traceback
from functools import wraps

import requests


N_RUNS = 500
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


n_calls = {
    ApiKeys.GROUPS: 0,
    ApiKeys.HISTORIES: 0,
    ApiKeys.SEND: 0,
}
t_calls = {
    ApiKeys.GROUPS: 0,
    ApiKeys.HISTORIES: 0,
    ApiKeys.SEND: 0,
}


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
                t_calls[key] += the_time
                n_calls[key] += 1
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
    )
    return r.json()


@timeit(ApiKeys.HISTORIES)
def call_histories(_group_id, _user_id):
    requests.post(
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
    )


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


def format_times():
    for key in ALL_API_KEYS:
        if n_calls[key] == 0:
            continue

        calls = n_calls[key]
        avg = t_calls[key] / n_calls[key]
        print(f"{key}: {calls}, avg. time {avg:.2f}ms")

    print()


for _ in range(N_RUNS):
    try:
        user = random.choice(USERS)
        groups = call_groups(user)

        if len(groups) and "detail" not in groups:
            for _ in range(max(5, min(5, len(groups)))):
                group = random.choice(groups)
                call_histories(group["group"]["group_id"], user)

                users = group["group"]["users"].split(",")
                receiver_ids = [int(a_user) for a_user in users if int(a_user) != user]
                if not len(receiver_ids):
                    continue

                receiver_id = receiver_ids[0]
                call_send(user, receiver_id)

            format_times()

    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        time.sleep(2)
    except KeyboardInterrupt:
        break
