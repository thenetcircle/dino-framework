import logging
import sys
import traceback
from datetime import datetime as dt

from dinofw import environ
from dinofw import utils
from dinofw.config import SessionKeys as S
from dinofw.utils.activity import ActivityBuilder

logger = logging.getLogger(__name__)


class OnLoginHooks:
    @staticmethod
    def update_session_and_join_private_room(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = utils.b64d(activity.actor.display_name)
        environ.env.session[S.user_id.value] = user_id
        environ.env.session[S.user_name.value] = user_name

        """
        try:
            user_agent_string = environ.env.request.user_agent.string or ""
            user_agent_platform = environ.env.request.user_agent.platform or ""
            user_agent_browser = environ.env.request.user_agent.browser or ""
            user_agent_version = environ.env.request.user_agent.version or ""
            user_agent_language = environ.env.request.user_agent.language or ""
        except Exception as e:
            logger.error(
                'could not get user agent for user "{}": {}'.format(user_id, str(e))
            )
            logger.exception(traceback.format_exc())
            environ.env.capture_exception(sys.exc_info())
            user_agent_string = ""
            user_agent_platform = ""
            user_agent_browser = ""
            user_agent_version = ""
            user_agent_language = ""

        session = environ.env.session

        session[S.user_agent.value] = user_agent_string
        session[S.user_agent_browser.value] = user_agent_browser
        session[S.user_agent_version.value] = user_agent_version
        session[S.user_agent_platform.value] = user_agent_platform
        session[S.user_agent_language.value] = user_agent_language

        user_info = {
            "last_login": dt.utcnow(),
        }
        environ.env.db.set_user_info(user_id, user_info)
        """

        environ.env.join_room(user_id)

    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = environ.env.session.get(S.user_name.value)

        activity_json = ActivityBuilder.activity_for_login(
            user_id, user_name, encode_attachments=False, include_history=False
        )

        environ.env.publish(activity_json, external=True)


@environ.env.observer.on("on_login")
def _on_login_set_user_online(arg: tuple) -> None:
    OnLoginHooks.update_session_and_join_private_room(arg)
    OnLoginHooks.publish_activity(arg)
