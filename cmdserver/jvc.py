from datetime import datetime
import enum
import logging
import socket

import select
import time

from cmdserver.jvccommands import WriteOnly, BinaryData, ReadOnly, NoVerify

PJ_ACK = b'PJACK'

PJ_REQ = b'PJREQ'

PJ_OK = b'PJ_OK'

DEFAULT_PORT = 20554

logger = logging.getLogger(__name__)


class Error(Exception):
    """Unspecified error"""
    pass


class BadData(Exception):
    def __init__(self, expected, actual):
        self.__expected = expected
        self.__actual = actual

    def __str__(self):
        return f"Expected {self.__expected}, received {self.__actual}"


class Closed(Exception):
    """Connection Closed"""
    pass


class Timeout(Exception):
    """Command Timout"""
    pass


class CommandNack(Exception):
    """JVC command not acknowledged"""
    pass


class Header(enum.Enum):
    """JVC command and response headers"""
    operation = b'!'
    reference = b'?'
    response = b'@'
    ack = b'\x06'


UNIT_ID = b'\x89\x01'


END = b'\x0a'


class Protocol:
    """JVC projector protocol, understands how to send commands and handle the responses"""
    def __init__(self, host):
        self.conn = Connection(host=host)
        self.reconnect = False

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self, exception, value, traceback):
        self.conn.__exit__(exception, value, traceback)

    def __cmd(self, cmdtype, cmd, sendrawdata=None, acktimeout=1):
        """Send command and optional raw data and wait for acks"""
        logger.debug(f"  > Cmd:{cmdtype} {cmdtype.value+cmd}")
        assert cmdtype == Header.operation or cmdtype == Header.reference

        retry_count = 1

        def do_send(f):
            nonlocal retry_count
            try:
                f()
            except Closed:
                self.reconnect = True
                if retry_count:
                    logger.warning(f"Connection closed, retry {retry_count}")
                    retry_count -= 1
                else:
                    raise
            except CommandNack:
                self.reconnect = True
                raise
            except:
                self.reconnect = True
                logger.exception(f"Unexpected exception for Cmd:{cmdtype} {cmdtype.value+cmd}")
                raise

        while True:
            if self.reconnect:
                self.conn.reconnect()
                self.reconnect = False
            do_send(lambda: self.__send_cmd(acktimeout, cmd, cmdtype))
            do_send(lambda: self.__send_raw_data(cmd, cmdtype, sendrawdata))
            break

    def __send_raw_data(self, cmd, cmdtype, sendrawdata):
        if sendrawdata is not None:
            self.conn.send(sendrawdata)
            if self.conn.expect(Header.ack.value + UNIT_ID + cmd[:2] + END, timeout=20) == -1:
                raise CommandNack(f"Data not acknowledged [{cmdtype} {len(sendrawdata)}]")

    def __send_cmd(self, acktimeout, cmd, cmdtype):
        data = cmdtype.value + UNIT_ID + cmd + END
        self.conn.send(data)
        if self.conn.expect(Header.ack.value + UNIT_ID + cmd[:2] + END, timeout=acktimeout) == -1:
            raise CommandNack(f"Command not acknowledged [{cmdtype} {data}]")

    def cmd_op(self, cmd, **kwargs):
        """Send operation command"""
        self.__cmd(Header.operation, cmd, **kwargs)

    def cmd_ref(self, cmd, **kwargs):
        """Send reference command and retrieve response"""
        self.__cmd(Header.reference, cmd, **kwargs)
        data = self.conn.recv()
        header = Header.response.value + UNIT_ID + cmd[:2]
        if not data.startswith(header):
            raise Exception('Expected response header', header, data)
        if not data.endswith(END):
            raise Exception('Expected END', END, data)
        res = data[len(header):-1]
        logger.debug(f"  < Response: {res}")
        return res

    def cmd_ref_bin(self, cmd, **kwargs):
        """Send command and retrieve binary response"""
        self.__cmd(Header.reference, cmd, **kwargs)
        try:
            res = self.conn.recv(timeout=10)
        except Timeout:
            self.reconnect = True
            raise
        logger.debug(f"  < Response:{res}")
        return res


class Connection:
    """JVC projector network connection, handles low level socket comms and connection initialisation """
    def __init__(self, host, port=DEFAULT_PORT):
        self.__socket = None
        self.__port = port
        self.__host = host
        self.__close_time = 0.0

    def connect(self):
        """Open network connection to projector and perform handshake"""
        if self.__socket is None:
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            request_time = time.time()
            to_wait = 1.0 - (request_time - self.__close_time)
            if 1 > to_wait > 0:
                close_time_fmt = datetime.fromtimestamp(self.__close_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                logger.info(f"Waiting {to_wait:.3f}s to reopen socket [closed at: {close_time_fmt}]")
                time.sleep(to_wait)
            try:
                logger.info(f"Connecting to {self.__host}:{self.__port}")
                self.__socket.settimeout(1)
                self.__socket.connect((self.__host, self.__port))
                logger.info(f"Connected to {self.__host}:{self.__port}")
                self.__init_pj()
            except socket.timeout:
                raise Timeout(f"Connection failed on timeout [{self.__host}:{self.__port}]")
            except Exception as err:
                raise Error(f"Connection failed [{self.__host}:{self.__port}]", err)

    def __init_pj(self):
        logger.debug(f">> Protocol init")
        self.expect(PJ_OK)
        self.send(PJ_REQ)
        self.expect(PJ_ACK)
        logger.debug(f"<< Protocol init")

    def __enter__(self):
        while True:
            try:
                self.connect()
            except Exception as e:
                logger.exception('Unexpected failure')
                self.close()
                raise e
            break

        return self

    def close(self, fail=True):
        if self.__socket is not None:
            logger.info(f"Closing connection to {self.__host}:{self.__port}")
            try:
                self.__socket.close()
                logger.info(f"Closed connection to {self.__host}:{self.__port}")
            except Exception as e:
                if fail is True:
                    raise e
                else:
                    logger.exception(f"Unable to close connection to {self.__host}:{self.__port}")
            finally:
                self.__socket = None
                self.__close_time = time.time()

    def __exit__(self, exception, value, traceback):
        self.close()

    def reconnect(self):
        self.close()
        self.connect()

    def send(self, data):
        if self.__socket:
            logger.debug(f"Sending {data} to {self.__host}:{self.__port}")
            try:
                self.__socket.send(data)
            except ConnectionAbortedError as err:
                raise Closed(err)
        else:
            raise Error('Unable to send, not connected')

    def recv(self, limit=1024, timeout=1):
        if timeout:
            ready = select.select([self.__socket], [], [], timeout)
            if not ready[0]:
                raise Timeout(f"{timeout} second timeout expired")
        data = self.__socket.recv(limit)
        if not len(data):
            raise Closed('Connection closed by projector')
        logger.debug(f"< Received:{data}")
        return data

    def expect(self, expected, timeout=1):
        """Receive data and compare it against expected data"""
        try:
            actual = self.recv(len(expected), timeout)
        except Timeout:
            return -1
        if actual != expected:
            raise BadData(expected, actual)
        else:
            return 0


class CommandExecutor:
    """ Provides ability to execute specific commands """
    def __init__(self, host):
        self.conn = Protocol(host)

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self, exception, value, traceback):
        self.conn.__exit__(exception, value, traceback)

    def connect(self):
        self.__enter__()

    def disconnect(self, fail=True):
        self.conn.conn.close(fail=fail)

    def get(self, cmd):
        """Send reference command and convert response"""
        if isinstance(cmd.value, bytes):
            raise NotImplementedError('Get is not implemented for {}'.format(cmd.name))
        cmdcode, valtype = cmd.value
        if issubclass(valtype, WriteOnly):
            raise TypeError('{} is a write only command'.format(cmd.name))
        response = self.conn.cmd_ref_bin(cmdcode) if issubclass(valtype, BinaryData) else self.conn.cmd_ref(cmdcode)
        return valtype(response)

    def set(self, cmd, val, verify=True):
        """Send operation command"""
        cmdcode, valtype = cmd.value
        assert not issubclass(valtype, ReadOnly), '{} is a read only command'.format(cmd)
        val = valtype(val)
        assert(isinstance(val, valtype)), '{} is not {}'.format(val, valtype)
        if issubclass(valtype, BinaryData):
            self.conn.cmd_op(cmdcode, sendrawdata=val.value)
        else:
            self.conn.cmd_op(cmdcode+val.value, acktimeout=5)

        if not verify or issubclass(valtype, NoVerify):
            return

        verify_val = self.get(cmd)
        if verify_val != val:
            raise CommandNack('Verify error: ' + cmd.name, val, verify_val)
