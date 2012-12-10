#!/usr/bin/env python2

# Copyright (c) 2012, Jason Chu <jchu@xentac.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies, 
# either expressed or implied, of the FreeBSD Project.

# Borrows ideas from https://github.com/uriel1998/volumerb
# Code was too ugly and too ruby to maintain

import subprocess
import sys
import re
import collections

class Pulse(object):
    def __init__(self):
        """Populate values"""

        output = subprocess.check_output(['pactl', 'list', 'sinks'])

        self.sinks = collections.defaultdict(dict)

        current_sink = None

        def update_sink_value(reg, line, boolean=False, integer=False):
            g = re.match(reg, line)
            if g:
                for key, value in g.groupdict().iteritems():
                    if boolean:
                        self.sinks[current_sink][key] = value == "yes"
                    elif integer:
                        self.sinks[current_sink][key] = int(value)
                    else:
                        self.sinks[current_sink][key] = value

        # Get most of the sink information
        for line in output.splitlines():
            g = re.match(r'^Sink #(?P<index>\d+)', line)
            if g:
                current_sink = g.group('index')
                self.sinks[current_sink]["sink"] = current_sink
            update_sink_value(r'^\W*Name: *(?P<name>.*)', line)
            update_sink_value(r'^\W*Volume: 0: *(?P<volume>\d+)', line, integer=True)
            update_sink_value(r'^\W*Mute: (?P<mute>.*)$', line, boolean=True)

        # Figure out the global information (like which sink is default)
        output = subprocess.check_output(['pactl', 'info'])

        for line in output.splitlines():
            g = re.match(r'^Default Sink: (?P<name>.*)', line)
            if g:
                # Which sink is this
                for sink, values in self.sinks.iteritems():
                    if values['name'] == g.group('name'):
                        values['default'] = True
                    else:
                        values['default'] = False

        import pprint; pprint.pprint(self.sinks)

    def volume_relative(self, amount):
        """Change the volume percentage by amount of all the sinks"""
        for sink, values in self.sinks.iteritems():
            new_volume = values['volume'] + amount
            new_volume = max(new_volume, 0)
            new_volume = min(new_volume, 100)
            values['volume'] = new_volume

            subprocess.call(['pactl', 'set-sink-volume', sink, str(new_volume) + '%'])

    def toggle_mute(self):
        for sink, values in self.sinks.iteritems():
            new_mute = '0' if values['mute'] else '1'
            values['mute'] = not values['mute']
            subprocess.call(['pactl', 'set-sink-mute', sink, new_mute])

    def get_simple_output(self):
        for sink, values in self.sinks.iteritems():
            if values['default']:
                return str(values['volume']) + ('%' if not values['mute'] else 'M')

def main(argv=None):
    """Where all the magic happens"""
    if argv is None:
        argv = []

    p = Pulse()

    if len(argv) > 1:
        if argv[1] == "up":
            p.volume_relative(5)
        elif argv[1] == "down":
            p.volume_relative(-5)
        elif argv[1] == "toggle":
            p.toggle_mute()

    print p.get_simple_output()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
