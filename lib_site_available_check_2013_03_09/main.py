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

import threading, argparse, configparser, heapq
from . import read_list, site_available_check

class UserError(Exception):
    pass

def on_begin(error, ui_lock, data):
    with ui_lock:
        if error is not None:
            print('error (on_begin): {!r}: {}'.format(error[0], error[1]))
            return
        
        print('[{!r}] begin: {!r}'.format(data.site_id, data.site_url))

def on_result(error, ui_lock, out_heap, data):
    with ui_lock:
        if error is not None:
            print('[{!r}] error: {!r}: {!r}: {}'.format(
                    data.site_id, data.site_url,
                    error[0], error[1]))
            return
        
        heapq.heappush(out_heap, (data.site_id, data))
        
        print('[{!r}] pass: {!r}'.format(data.site_id, data.site_url))

def on_done(error, ui_lock, out_heap, out_fd, done_event):
    with ui_lock:
        try:
            if error is not None:
                print('error (on_done): {!r}: {}'.format(error[0], error[1]))
                return
            
            print('writing...')
            
            while True:
                try:
                    site_id, data = heapq.heappop(out_heap)
                except IndexError:
                    break
                
                out_fd.write('{}\n'.format(data.site_url))
                out_fd.flush()
            
            print('done!')
        finally:
            done_event.set()

def main():
    parser = argparse.ArgumentParser(
            description='tiny simple utility '
                    'for massive checking sites for available (status 200)',
            )
    parser.add_argument(
            'in_site_list',
            metavar='INPUT-SITE-LIST-PATH',
            help='path to input file of site list',
            )
    parser.add_argument(
            'out_site_list',
            metavar='OUTPUT-SITE-LIST-PATH',
            help='path to output file of result available site list',
            )
    
    args = parser.parse_args()
    
    ui_lock = threading.RLock()
    
    site_list = read_list.read_list(args.in_site_list)
    out_heap = []
    
    with open(args.out_site_list, 'w', encoding='utf-8', newline='\n') as out_fd:
        done_event = threading.Event()
        site_available_check.bulk_site_available_check(
                site_list,
                on_begin=lambda error, data: on_begin(error, ui_lock, data),
                on_result=lambda error, data: on_result(error, ui_lock, out_heap, data),
                callback=lambda error: on_done(error, ui_lock, out_heap, out_fd, done_event),
                )
        done_event.wait()
