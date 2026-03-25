import logging
from typing import List, Dict, Any
import tornado.web
import tornado.ioloop

from tornado.options import options
from webssh import handler
from webssh.handler import IndexHandler, WsockHandler, NotFoundHandler
from webssh.worker import check_session_timeout
from webssh.settings import (
    get_app_settings,  get_host_keys_settings, get_policy_setting,
    get_ssl_context, get_server_settings, check_encoding_setting
)


def make_handlers(loop: tornado.ioloop.IOLoop, options: Any) -> List[tuple]:
    host_keys_settings = get_host_keys_settings(options)
    policy = get_policy_setting(options, host_keys_settings)

    handlers = [
        (r'/', IndexHandler, dict(loop=loop, policy=policy,
                                  host_keys_settings=host_keys_settings)),
        (r'/ws', WsockHandler, dict(loop=loop))
    ]
    return handlers


def make_app(handlers: List[tuple], settings: Dict[str, Any]) -> tornado.web.Application:
    settings.update(default_handler_class=NotFoundHandler)
    return tornado.web.Application(handlers, **settings)


def app_listen(app: tornado.web.Application, port: int, address: str, server_settings: Dict[str, Any]) -> None:
    app.listen(port, address, **server_settings)
    if not server_settings.get('ssl_options'):
        server_type = 'http'
    else:
        server_type = 'https'
        handler.redirecting = True if options.redirect else False
    logging.info(
        'Listening on {}:{} ({})'.format(address, port, server_type)
    )


def main() -> None:
    options.parse_command_line()
    check_encoding_setting(options.encoding)
    loop = tornado.ioloop.IOLoop.current()
    app = make_app(make_handlers(loop, options), get_app_settings(options))
    ssl_ctx = get_ssl_context(options)
    server_settings = get_server_settings(options)
    app_listen(app, options.port, options.address, server_settings)
    if ssl_ctx:
        server_settings.update(ssl_options=ssl_ctx)
        app_listen(app, options.sslport, options.ssladdress, server_settings)
    
    # Periodic cleanup of rate limiter to prevent memory buildup
    tornado.ioloop.PeriodicCallback(
        handler.rate_limiter.cleanup, 
        options.ratelimit_window * 1000  # Convert to milliseconds
    ).start()
    
    # Periodic check for session timeouts
    if options.session_timeout > 0:
        tornado.ioloop.PeriodicCallback(
            lambda: check_session_timeout(options),
            60 * 1000  # Check every 60 seconds
        ).start()
        logging.info('Session timeout enabled: {} seconds'.format(options.session_timeout))
    
    loop.start()


if __name__ == '__main__':
    main()
