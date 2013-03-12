# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2013 Andrej A Antonov <polymorphm@gmail.com>.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

assert str is not bytes

import sys, threading
from urllib import request

DEFAULT_CONCURRENCY = 20

class SiteAvCheckError(Exception):
    pass

class SiteAvCheckData:
    pass

def fix_url(raw_url):
    assert isinstance(raw_url, str)
    
    if not raw_url.startswith('https:') and \
            not raw_url.startswith('http:'):
        if not raw_url.startswith('/'):
            raw_url = '/{}'.format(raw_url)
        if not raw_url.startswith('//'):
            raw_url = '/{}'.format(raw_url)
        
        raw_url = 'http:{}'.format(raw_url)
    
    return raw_url

def site_available_check_thread(
        iter_lock,
        site_iter,
        on_begin=None,
        on_result=None,
        ):
    while True:
        data = SiteAvCheckData()
        
        try:
            with iter_lock:
                try:
                    data.site_id, data.site_raw_url = next(site_iter)
                except StopIteration:
                    return
            
            data.site_url = fix_url(data.site_raw_url)
            data.opener_req = request.Request(data.site_url)
            data.opener_timeout = 20.0
            data.opener_data_require = 1000
        except Exception:
            if on_begin is not None:
                on_begin(sys.exc_info(), data)
            
            continue
        else:
            if on_begin is not None:
                on_begin(None, data)
        
        try:
            opener = request.build_opener()
            resp = opener.open(
                    data.opener_req,
                    timeout=data.opener_timeout,
                    )
            
            if resp.getcode() != 200:
                raise SiteAvCheckError('resp.getcode() not equals 200')
            
            data.resp_data = resp.read(data.opener_data_require)
            
            if len(data.resp_data) < data.opener_data_require:
                raise SiteAvCheckError('len(data.resp_data) less then data.opener_data_require')
        except Exception:
            if on_result is not None:
                on_result(sys.exc_info(), data)
            
            continue
        else:
            if on_result is not None:
                on_result(None, data)

def bulk_site_available_check(
        site_list,
        conc=None,
        on_begin=None,
        on_result=None,
        callback=None,
        ):
    if conc is None:
        conc = DEFAULT_CONCURRENCY
    
    iter_lock = threading.RLock()
    site_iter = enumerate(site_list)
    
    thread_list = tuple(
            threading.Thread(
                    target=lambda: site_available_check_thread(
                            iter_lock,
                            site_iter,
                            on_begin=on_begin,
                            on_result=on_result,
                            ),
                    )
            for thread_i in range(conc)
            )
    
    for thread in thread_list:
        thread.start()
    
    def in_thread():
        for thread in thread_list:
            thread.join()
        
        if callback is not None:
            callback(None)
    
    threading.Thread(target=in_thread).start()
