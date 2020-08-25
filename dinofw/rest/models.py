from datetime import datetime as dt
from typing import Optional, List

import pytz
import arrow
from pydantic import BaseModel


class AbstractQuery(BaseModel):
    @staticmethod
    def to_dt(s, allow_none: bool = False, default: dt = None) -> Optional[dt]:
        if s is None and default is not None:
            return default

        if s is None and allow_none:
            return None

        if s is None:
            s = arrow.utcnow().datetime
        else:
            s = dt.fromtimestamp(s).replace(tzinfo=pytz.UTC)

        return s

    @staticmethod
    def to_ts(ds, allow_none: bool = False) -> Optional[str]:
        if ds is None and allow_none:
            return None

        if ds is None:
            ds = arrow.utcnow().datetime

        return ds.strftime("%s.%f")


class PaginationQuery(AbstractQuery):
    until: Optional[float]
    per_page: int


class AdminQuery(AbstractQuery):
    admin_id: Optional[int]


class MessageQuery(PaginationQuery, AdminQuery):
    message_type: Optional[int]
    status: Optional[int]


class UpdateHighlightQuery(AbstractQuery):
    highlight_time: float


class CreateActionLogQuery(AdminQuery):
    user_ids: List[int]
    action_type: int


class SearchQuery(PaginationQuery):
    keyword: Optional[str]
    group_type: Optional[int]
    status: Optional[int]


class SendMessageQuery(AbstractQuery):
    message_payload: str
    message_type: str


class CreateGroupQuery(AbstractQuery):
    group_name: str
    group_type: int
    users: List[int]
    description: Optional[str]
    meta: Optional[int]
    context: Optional[str]
    weight: Optional[int]


class GroupQuery(PaginationQuery):
    ownership: Optional[int]
    weight: Optional[int]
    has_unread: Optional[int]


class UpdateGroupQuery(AbstractQuery):
    status: Optional[int]
    owner: Optional[int]
    name: Optional[str]
    weight: Optional[int]
    context: Optional[str]


class EditMessageQuery(AdminQuery):
    message_payload: Optional[str]
    message_type: Optional[int]
    status: Optional[int]


class UpdateUserGroupStats(AbstractQuery):
    last_read_time: Optional[float]
    delete_before: Optional[float]
    hide: Optional[bool]
    bookmark: Optional[bool]
    pin: Optional[bool]


class Message(BaseModel):
    group_id: str
    created_at: float
    user_id: int
    message_id: str
    message_payload: str

    status: Optional[int]
    message_type: Optional[str]
    updated_at: Optional[float]
    removed_at: Optional[float]
    removed_by_user: Optional[int]
    last_action_log_id: Optional[str]


class GroupJoinTime(BaseModel):
    user_id: int
    join_time: float


class GroupLastRead(BaseModel):
    user_id: int
    last_read: float


class GroupUsers(BaseModel):
    group_id: str
    owner_id: int
    user_count: int
    users: List[GroupJoinTime]


class UserStats(BaseModel):
    user_id: int
    unread_amount: int
    group_amount: int
    owned_group_amount: int
    last_update_time: Optional[float]
    last_read_time: Optional[float]
    last_read_group_id: Optional[str]
    last_send_time: Optional[float]
    last_send_group_id: Optional[str]


class UserGroupStats(BaseModel):
    group_id: str
    user_id: int
    message_amount: int
    unread_amount: int
    last_read_time: float
    last_send_time: float
    delete_before: float
    highlight_time: Optional[float]

    hide: bool
    pin: bool
    bookmark: bool


class ActionLog(BaseModel):
    action_id: str
    user_id: int
    group_id: str
    action_type: int
    created_at: float
    admin_id: Optional[int]
    message_id: Optional[str]


class Group(BaseModel):
    group_id: str
    users: List[GroupJoinTime]
    user_count: int
    last_read: float
    name: str
    description: Optional[str]
    status: Optional[int]
    group_type: int
    created_at: float
    updated_at: Optional[float]
    owner_id: int
    meta: Optional[int]
    context: Optional[str]
    weight: Optional[str]
    last_message_overview: Optional[str]
    last_message_time: float

    highlight_time: Optional[float]
    pin: Optional[bool]
    bookmark: Optional[bool]


class Histories(BaseModel):
    messages: List[Message]
    action_logs: List[ActionLog]
    last_reads: List[GroupLastRead]