import logging

from dinofw.utils.activity import ActivityBuilder

from dinofw import environ
from dinofw.config import ConfigKeys

logger = logging.getLogger(__name__)


class OnStartupDoneHooks(object):
    @staticmethod
    def publish_startup_done_event() -> None:
        if len(environ.env.config) == 0 or environ.env.config.get(
            ConfigKeys.TESTING, False
        ):
            # assume we're testing
            return

        if environ.env.node != "web":
            # avoid publishing duplicate events by only letting the web node publish external events
            return

        json_event = ActivityBuilder.enrich(
            {
                "verb": "restart",
                "content": environ.env.config.get(ConfigKeys.ENVIRONMENT),
            }
        )

        logger.debug(
            "publishing restart-done event to external queue: %s" % str(json_event)
        )
        environ.env.publish(json_event, external=True)


@environ.env.observer.on("on_startup_done")
def _on_startup_done(arg) -> None:
    OnStartupDoneHooks.publish_startup_done_event()
