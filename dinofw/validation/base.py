from dinofw import environ
from activitystreams import Activity

from dinofw.config import SessionKeys


class BaseValidator:
    def validate_request(self, activity: Activity) -> (bool, str):
        if not hasattr(activity.actor, "id") or activity.actor.id is None:
            return False, "no ID on actor"

        session_user_id = environ.env.session.get("user_id", "NOT_FOUND_IN_SESSION")
        if str(activity.actor.id).strip() != str(session_user_id).strip():
            error_msg = "user_id in session '%s' doesn't match user_id in request '%s'"
            return False, error_msg % (session_user_id, activity.actor.id)

        return True, None

    def validate_login(self, user_id: str, token: str) -> (bool, str):
        """
        checks whether required data was received and that it validates with community (not tampered with)

        :param user_id: the id of the user
        :param token: the token of the user to verify
        :return: tuple(Boolean, String): (is_valid, error_message)
        """
        (
            is_valid,
            error_msg,
            session,
        ) = environ.env.auth.authenticate_and_populate_session(user_id, token)
        if not is_valid:
            return False, error_msg, None

        is_valid, error_msg = self.validate_session(session)
        return is_valid, error_msg, session

    def validate_session(self, session: dict) -> (bool, str):
        """
        validate that all required parameters were send from the client side

        :param session: the session dict to validate
        :return: tuple(Boolean, String): (is_valid, error_message)
        """
        for session_key in SessionKeys:
            key = session_key.value

            if key not in SessionKeys.requires_session_keys.value:
                continue

            if key not in session:
                return False, '"%s" is a required parameter' % key

            val = session[key]
            if val is None or val == "":
                return False, '"%s" is a required parameter' % key
        return True, None
