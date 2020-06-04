from flask import Flask
from flask_restful import Api

from dinofw import environ
from dinofw.rest.resources.send import SendResource

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from werkzeug.contrib.fixers import ProxyFix

from dinofw.config import ConfigKeys

logger = logging.getLogger(__name__)
logging.getLogger("amqp").setLevel(logging.INFO)
logging.getLogger("kafka.conn").setLevel(logging.INFO)


def create_app():
    _app = Flask(__name__)

    # used for encrypting cookies for handling sessions
    _app.config["SECRET_KEY"] = "abc492ee-9739-11e6-a174-07f6b92d4a4b"

    queue_host = environ.env.config.get(
        ConfigKeys.HOST, domain=ConfigKeys.COORDINATOR, default=""
    )

    message_db = environ.env.config.get(
        ConfigKeys.DB, domain=ConfigKeys.COORDINATOR, default=0
    )
    message_env = environ.env.config.get(ConfigKeys.ENVIRONMENT, default="test")
    message_channel = "dino_{}_{}".format(message_env, message_db)
    message_queue = "redis://{}".format(queue_host)

    logger.info("message_queue: %s" % message_queue)

    _api = Api(_app)

    _socketio = SocketIO(
        _app,
        logger=logger,
        engineio_logger=os.environ.get("DINO_DEBUG", "0") == "1",
        async_mode="eventlet",
        message_queue=message_queue,
        channel=message_channel,
    )

    # preferably "emit" should be set during env creation, but the socketio object is not created until after env is
    environ.env.out_of_scope_emit = _socketio.emit

    _app.wsgi_app = ProxyFix(_app.wsgi_app)
    return _app, _api, _socketio


app, api, socketio = create_app()

api.add_resource(SendResource, "/send")