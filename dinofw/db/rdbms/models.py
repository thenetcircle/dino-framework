from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime

from dinofw.environ import env


class GroupEntity(env.Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)

    group_id = Column(String(36), nullable=False, index=True)
    name = Column(String(128), nullable=False)

    status = Column(Integer, nullable=True)
    group_type = Column(Integer, nullable=False, server_default='0')
    last_message_time = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    owner_id = Column(Integer, nullable=False)

    updated_at = Column(DateTime)
    group_meta = Column(Integer)
    group_weight = Column(Integer)
    group_context = Column(String(512))
    description = Column(String(256))
    last_message_overview = Column(String(256))


class UserStatsEntity(env.Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)

    group_id = Column(String(36), index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)

    last_read = Column(DateTime, nullable=False)
    last_sent = Column(DateTime, nullable=False)
    hide_before = Column(DateTime, nullable=False)
