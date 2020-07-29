from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from dinofw.config import ConfigKeys


def init_db(env, engine=None):
    if engine is None:
        database_uri = env.config.get(ConfigKeys.URI, domain=ConfigKeys.DB)

        connection_args = dict()
        if database_uri.startswith("sqlite"):
            connection_args = {"check_same_thread": False}
        else:
            connection_args = {"options": "-c timezone=utc"}

        engine = create_engine(database_uri, connect_args=connection_args)

    env.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    env.Base = declarative_base()

    from dinofw.db.rdbms.models import GroupEntity, UserGroupStatsEntity

    env.Base.metadata.create_all(bind=engine)
