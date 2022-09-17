# Copyright (C) 2013 by Aivars Kalvans <aivars.kalvans@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import re
import random
import base64
import contextlib
import logging

CUSTOM_PROXY_REGEX = '(\w+://)([^:]+?:[^@]+?@)?(.+)'

log = logging.getLogger('scrapy.proxies')


class Mode:
    RANDOMIZE_PROXY_EVERY_REQUESTS, RANDOMIZE_PROXY_ONCE, SET_CUSTOM_PROXY = range(3)


class RandomProxy(object):
    proxy_matcher = re.compile(CUSTOM_PROXY_REGEX)

    def _select_proxy(self):
        if self.mode == Mode.RANDOMIZE_PROXY_ONCE:
            return self.chosen_proxy or random.choice(list(self.proxies.keys()))
        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS:
            return random.choice(list(self.proxies.keys()))
        return self.chosen_proxy

    def __init__(self, settings):
        self.mode = settings.get('PROXY_MODE')
        self.proxy_list = settings.get('PROXY_LIST')
        self.chosen_proxy = ''
        if self.mode in [Mode.RANDOMIZE_PROXY_EVERY_REQUESTS, Mode.RANDOMIZE_PROXY_ONCE]:
            self._parse_proxies()
        elif self.mode == Mode.SET_CUSTOM_PROXY:
            self._parse_custom_proxies(settings)

    def _parse_custom_proxies(self, settings):
        custom_proxy = settings.get('CUSTOM_PROXY')
        self.proxies = {}
        parts = self.proxy_matcher.match(custom_proxy.strip())
        if not parts:
            raise ValueError('CUSTOM_PROXY is not well formatted')
        user_pass = parts[2][:-1] if parts[2] else ''
        self.proxies[parts[1] + parts[3]] = user_pass
        self.chosen_proxy = parts[1] + parts[3]

    def _parse_proxies(self):
        if self.proxy_list is None:
            raise KeyError('PROXY_LIST setting is missing')
        self.proxies = {}
        fin = open(self.proxy_list)
        try:
            for line in fin:
                parts = self.proxy_matcher.match(line.strip())
                if not parts:
                    continue
                user_pass = parts[2][:-1] if parts[2] else ''
                self.proxies[parts[1] + parts[3]] = user_pass
        finally:
            fin.close()
        self.chosen_proxy = self._select_proxy()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        # Don't overwrite with a random one (server-side state for IP)
        if 'proxy' in request.meta and request.meta["exception"] is False:
            return
        request.meta["exception"] = False
        if len(self.proxies) == 0:
            raise ValueError('All proxies are unusable, cannot proceed')
        proxy_address = self._select_proxy()
        request.meta['proxy'] = proxy_address
        if proxy_user_pass := self.proxies[proxy_address]:
            basic_auth = f'Basic {base64.b64encode(proxy_user_pass.encode()).decode()}'
            request.headers['Proxy-Authorization'] = basic_auth

        log.debug('Using proxy <%s>, %d proxies left' % (proxy_address, len(self.proxies)))

    def process_exception(self, request, exception, spider):
        if 'proxy' not in request.meta:
            return
        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS:
            proxy = self._extracted_from_process_exception(request)
            log.info('Removing failed proxy <%s>, %d proxies left' % (proxy, len(self.proxies)))

        elif self.mode == Mode.RANDOMIZE_PROXY_ONCE:
            proxy = self._extracted_from_process_exception(request)
            self.chosen_proxy = self._select_proxy()
            log.info('Removing failed proxy <%s>, %d proxies left' % (proxy, len(self.proxies)))

    def _extracted_from_process_exception(self, request):
        result = request.meta['proxy']
        with contextlib.suppress(KeyError):
            del self.proxies[result]
        request.meta["exception"] = True
        return result
