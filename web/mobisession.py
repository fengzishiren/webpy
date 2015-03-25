#!/usr/bin/env python
# -*- coding:utf-8 -*-

import copy
import os
import time
import web

try:
    import hashlib

    sha1 = hashlib.sha1
except ImportError:
    import sha

    sha1 = sha.new

__author__ = 'richardzheng'


class MobiSession(object):
    """
    Session management for web.py
    Note: set web.config.debug=False
    """
    __slots__ = [
        "store", "_initializer", "_last_cleanup_time", "_config", "_data",
        "__getitem__", "__setitem__", "__delitem__"
    ]

    def __init__(self, app, store, initializer=None, tok_name='access_token', timeout=60 * 60 * 24 * 30):
        self.store = store
        self._initializer = initializer
        self._last_cleanup_time = 0
        self._config = web.utils.storage(tok_name=tok_name, timeout=timeout, secret_key='fLjUfxqXtfNoIldA0A0J')
        self._data = web.utils.threadeddict()  # thread local for multithread of python not multiprocess
        self.__getitem__ = self._data.__getitem__
        self.__setitem__ = self._data.__setitem__
        self.__delitem__ = self._data.__delitem__
        if app:
            app.add_processor(self._processor)

    def create(self, uid):
        """Generate a random id for session"""

        while True:
            rand = os.urandom(16)
            now = time.time()
            secret_key = self._config.secret_key
            session_id = sha1("%s%s%s%s" % (rand, now, '0.0.0.0', secret_key))
            session_id = session_id.hexdigest()
            if session_id not in self.store:
                break
        # bypass self.__setattr__
        self._data.session_id = session_id
        self._data.uid = uid

        if self._initializer:
            if isinstance(self._initializer, dict):
                self.update(copy.deepcopy(self._initializer))
            elif hasattr(self._initializer, '__call__'):
                self._initializer()
        return session_id

    def _processor(self, handler):
        """Application processor to setup session for every request"""
        self._cleanup()
        self._load()
        try:
            return handler()
        finally:
            self._save()

    def __contains__(self, name):
        return name in self._data

    def __getattr__(self, name):
        return getattr(self._data, name) if hasattr(self._data, name) else None

    def __setattr__(self, name, value):
        if name in self.__slots__:
            object.__setattr__(self, name, value)
        else:
            if self.session_id:
                setattr(self._data, name, value)
            else:
                raise AttributeError("not found '%s'" % name)

    def __delattr__(self, name):
        delattr(self._data, name)

    def _load(self):
        """
        don't create new session by default state
        :return:
        """
        session_id = web.input().pop(self._config.tok_name, None)
        if session_id and self._valid_session_id(session_id) and session_id in self.store:
            d = self.store[session_id]
            self.update(d)

    def _cleanup(self):
        """Cleanup the stored sessions"""
        current_time = time.time()
        timeout = self._config.timeout
        if current_time - self._last_cleanup_time > timeout:
            self.store.cleanup(timeout)
            self._last_cleanup_time = current_time

    def _valid_session_id(self, session_id):
        rx = web.utils.re_compile('^[0-9a-fA-F]+$')
        return rx.match(session_id)

    def _save(self):
        if self.session_id:
            self.store[self.session_id] = dict(self._data)
            self.session_id = None

    def kill(self):
        """Kill the session, make it no longer available"""
        if self.session_id:
            del self.store[self.session_id]
            self.session_id = None

    def raw_data(self):
        return dict(self._data)


class VisualMobiSession(MobiSession):
    def load(self, session_id=None):
        session_id = session_id if session_id else web.input().get(self._config.tok_name)
        if session_id and self._valid_session_id(session_id) and session_id in self.store:
            d = self.store[session_id]
            self.update(d)

    def save(self):
        self._save()


if __name__ == '__main__':
    s = VisualMobiSession(None, web.session.DiskStore('sessions'), {'login': 0})
    print '----------no session-----------'
    print s.raw_data(), s.login, s.email, s.uid, s.session_id

    print '--------create serssion----------'
    access_token = s.create('08110')
    # s.load('6b829e0820f3b5d94b3e35508c9c2e69c157ad29')
    print s.raw_data()
    print s.login, s.email, s.uid
    s.email = 'zhenglinhai@baidu.com'
    print s.raw_data()
    s.update({'count': 0})
    print s.raw_data()
    s.save()
    print '--------load session--------'
    s.load(access_token)
    print s.raw_data(), s.login, s.email, s.uid, s.session_id


