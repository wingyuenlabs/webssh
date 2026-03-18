import logging
import time
from typing import Dict, Optional, Tuple
try:
    import secrets
except ImportError:
    secrets = None
import tornado.websocket
import paramiko

from uuid import uuid4
from tornado.ioloop import IOLoop
from tornado.iostream import _ERRNO_CONNRESET
from tornado.util import errno_from_exception


BUF_SIZE = 32 * 1024
clients: Dict[str, Dict[str, 'Worker']] = {}  # {ip: {id: worker}}


def clear_worker(worker: 'Worker', clients: Dict[str, Dict[str, 'Worker']]) -> None:
    ip = worker.src_addr[0]
    workers = clients.get(ip)
    assert worker.id in workers
    workers.pop(worker.id)

    if not workers:
        clients.pop(ip)
        if not clients:
            clients.clear()


def recycle_worker(worker: 'Worker') -> None:
    if worker.handler:
        return
    logging.warning('Recycling worker {}'.format(worker.id))
    worker.close(reason='worker recycled')


class Worker(object):
    def __init__(self, loop: IOLoop, ssh: paramiko.SSHClient, chan: paramiko.Channel, dst_addr: Tuple[str, int]):
        self.loop = loop
        self.ssh = ssh
        self.chan = chan
        self.dst_addr = dst_addr
        self.fd = chan.fileno()
        self.id = self.gen_id()
        self.data_to_dst = []
        self.handler = None
        self.mode = IOLoop.READ
        self.closed = False
        self.last_activity = time.time()
        # NO-OP callback will be set from main thread after creation
        self._noop_callback = None

    def _send_noop(self):
        if self.closed:
            return
        try:
            transport = self.ssh.get_transport()
            if transport and transport.is_active():
                transport.send_ignore()
                logging.debug(f"Sent SSH NO-OP (keepalive) for worker {self.id}")
        except Exception as e:
            logging.warning(f"Failed to send SSH NO-OP for worker {self.id}: {e}")

    def __call__(self, fd, events):
        if events & IOLoop.READ:
            self.on_read()
        if events & IOLoop.WRITE:
            self.on_write()
        if events & IOLoop.ERROR:
            self.close(reason='error event occurred')

    @classmethod
    def gen_id(cls) -> str:
        return secrets.token_urlsafe(nbytes=32) if secrets else uuid4().hex

    def set_handler(self, handler):
        if not self.handler:
            self.handler = handler

    def update_handler(self, mode):
        if self.mode != mode:
            self.loop.update_handler(self.fd, mode)
            self.mode = mode
        if mode == IOLoop.WRITE:
            self.loop.call_later(0.1, self, self.fd, IOLoop.WRITE)

    def on_read(self):
        logging.debug('worker {} on read'.format(self.id))
        self.last_activity = time.time()
        try:
            data = self.chan.recv(BUF_SIZE)
        except (OSError, IOError) as e:
            logging.error(e)
            if self.chan.closed or errno_from_exception(e) in _ERRNO_CONNRESET:
                self.close(reason='chan error on reading')
        else:
            logging.debug('{!r} from {}:{}'.format(data, *self.dst_addr))
            if not data:
                self.close(reason='chan closed')
                return

            logging.debug('{!r} to {}:{}'.format(data, *self.handler.src_addr))
            try:
                self.handler.write_message(data, binary=True)
            except tornado.websocket.WebSocketClosedError:
                self.close(reason='websocket closed')

    def on_write(self):
        logging.debug('worker {} on write'.format(self.id))
        self.last_activity = time.time()
        if not self.data_to_dst:
            return

        # Properly handle both string and binary data
        if isinstance(self.data_to_dst[0], bytes):
            data = b''.join(self.data_to_dst)
        else:
            data = ''.join(self.data_to_dst)
        logging.debug('{!r} to {}:{}'.format(data, *self.dst_addr))

        try:
            sent = self.chan.send(data)
        except (OSError, IOError) as e:
            logging.error(e)
            if self.chan.closed or errno_from_exception(e) in _ERRNO_CONNRESET:
                self.close(reason='chan error on writing')
            else:
                self.update_handler(IOLoop.WRITE)
        else:
            self.data_to_dst = []
            data = data[sent:]
            if data:
                self.data_to_dst.append(data)
                self.update_handler(IOLoop.WRITE)
            else:
                self.update_handler(IOLoop.READ)

    def close(self, reason: Optional[str] = None) -> None:
        if self.closed:
            return
        self.closed = True

        # Stop the NO-OP callback
        if hasattr(self, '_noop_callback') and self._noop_callback is not None:
            try:
                self._noop_callback.stop()
            except Exception:
                pass
            self._noop_callback = None

        logging.info(
            'Closing worker {} with reason: {}'.format(self.id, reason)
        )
        if self.handler:
            self.loop.remove_handler(self.fd)
            self.handler.close(reason=reason)
        self.chan.close()
        self.ssh.close()
        logging.info('Connection to {}:{} lost'.format(*self.dst_addr))

        clear_worker(self, clients)
        logging.debug(clients)


def check_session_timeout(options):
    """Check and close timed-out sessions"""
    if options.session_timeout <= 0:
        return
    
    now = time.time()
    timeout = options.session_timeout
    expired_workers = []
    
    # Create a copy to avoid issues with concurrent modifications
    try:
        clients_copy = dict(clients)
    except RuntimeError:
        # Dictionary changed during iteration, skip this round
        return
    
    for ip, workers in clients_copy.items():
        if not workers:
            continue
        
        # Create a copy of workers dict as well
        try:
            workers_copy = dict(workers)
        except RuntimeError:
            continue
            
        for worker_id, worker in workers_copy.items():
            # Check if worker is valid and has last_activity attribute
            if worker is None:
                continue
            if not hasattr(worker, 'last_activity'):
                continue
            if worker.closed:
                continue
                
            try:
                if now - worker.last_activity > timeout:
                    expired_workers.append(worker)
            except (AttributeError, TypeError):
                # Worker might have been cleaned up
                continue
    
    for worker in expired_workers:
        try:
            logging.warning('Session {} timed out after {} seconds of inactivity'.format(
                worker.id, timeout
            ))
            worker.close(reason='session timeout')
        except Exception as e:
            logging.error('Error closing timed-out worker: {}'.format(e))
