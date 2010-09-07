#!/usr/bin/env python
#
# munin_nag.py - Script to pass munin alerts into Nagios, using
#                a normalized plugin name.
#
# Enable this in munin by writing:
#  contact.nag.command /some/where/munin_nag.py /some/where/rw/nagios.cmd "${var:host}" "${var:graph_title}"
#  contact.nag.always_send warning critical
#
#
# This script will talk directly to nagios, not using nsca, so it requires
# that munin and nagios run on the same machine, and munin must be given
# permissions to write to the nagios command file specified in the first
# commandline parameter.
#
#
#
#
# Copyright (C) 2010 Magnus Hagander <magnus@hagander.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2 dated June,
# 1991.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA.
#

import sys
import re
import time
from optparse import OptionParser

# Keep in sync with munin2nagios.py
norm_re = re.compile('[^a-z0-9 ]', re.IGNORECASE)
def normalize_plugin_name(name):
	return norm_re.sub('',name.strip().replace("%","percent"))

if __name__=="__main__":
	opt = OptionParser(usage="%prog <nagioscommand> <host> <graph> [options]")

	(options, args) = opt.parse_args()
	if len(args) != 3:
		opt.print_help()
		sys.exit(1)

	# Slurp the whole input, put it in a single field,
	# and hand this off to nagios.
	msg = "".join(sys.stdin.readlines()).replace("\n"," ")

	# Figure out the worst alert level, and use that one
	alertlevel = 0 # OK
	if msg.find("UNKNOWNs") > 0:
		alertlevel = 3 # UNKNOWN
	if msg.find("WARNINGs") > 0:
		alertlevel = 1 # WARNING
	if msg.find("CRITICALs") > 0:
		alertlevel = 2 # CRITICAL

	# Connect to nagios and send the message
	f = open(args[0], "a")
	if not f:
		print "Failed to open nagios command channel %s" % args[0]
		sys.exit(1)

	f.write("[%s] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%s;%s\n" % (
			int(time.time()),
			args[1].split('.')[0],
			normalize_plugin_name(args[2]),
			alertlevel,
			msg
			))
	f.close()
