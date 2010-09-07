#!/usr/bin/env python
#
# munin2nagios.py - script to synchronize nagios passive checks
#                   with nodes and plugins from Munin that have
#                   warning or critical level set.
#                   Note that this script is intended to be used
#                   togheter with munin_nag.py instead of using
#                   the default Munin nagios alerting functionality,
#                   in order to use the service names properly.
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
from optparse import OptionParser
import re

from munin_nag import normalize_plugin_name

# Global var(s)
options = None


class Check(object):
	def __init__(self):
		self.title = None
		self.haslevel = False
		self.hostname = None
		self.pluginname = None

	def ParseLine(self, s):
		a = l.split(None,1)  # Splits into attribute name and value
		b = a[0].split(':')  # Splits into nodeinfo, plugin
		c = b[0].split(';')  # Splits into domain and nodename
		d = b[1].split('.')  # Splits into plugin, value and attribute

		if not self.hostname:
			self.hostname = c[1]
			self.pluginname = d[0]

		if self.hostname != c[1] or self.pluginname != d[0]:
			# Info changed, end of this plugin
			return False

		if len(d) > 1 and d[1] == "graph_title":
			self.title = a[1]

		if b[1].endswith('.critical') or b[1].endswith('warning'):
			self.haslevel = True

		return True

	def __str__(self):
		return "%s:%s %s" % (self.hostname, self.pluginname, self.haslevel)

	def get_nagios_config(self):
		template = (x for x in options.templates if x.ismatch(self.pluginname)).next()

		if not template.include():
			return "# Service %s excluded" % (self.pluginname)

		for x in options.hosts:
			if x.exclude(self.hostname):
				return "# Host %s excluded (service %s)" % (self.hostname, self.pluginname)

		return """define service {
	host_name             %s
	service_description   %s
	use                   %s
	}""" % (
	self.hostname.split('.')[0], normalize_plugin_name(self.title), template)


class Template(object):
	"""
	Contains a mapping from Munin plugin name to Nagios service
	template.

	A base template - one with no regexp - will map all plugins
	to the template. Any template that includes a regexp will map
	only those that match the given regex. For this reason, ordering
	of the temlplates is significant.
	"""
	def __init__(self, pattern):
		if pattern.find('/') > 0:
			pieces = pattern.rsplit('/',2)
			self.match = re.compile(pieces[0])
			self.template = pieces[1]
		else:
			# Base pattern, no regexp
			self.match = None
			self.template = pattern

	def __str__(self):
		return self.template

	def ismatch(self, str):
		"""
		Returns true if this template matches the given plugin title.
		If the pattern is a base pattern, it always returns true.
		"""
		if self.match:
			return self.match.match(str)
		# Base patterns match everything
		return True

	def include(self):
		"""
		Returns true if this service check should be included.
		"""
		if len(self.template) == 0:
			return False
		return True

class HostExclude(object):
	def __init__(self, pattern):
		self.re = re.compile(pattern)

	def exclude(self, str):
		return self.re.match(str)

if __name__=="__main__":
	opt = OptionParser(usage="%prog -f FILENAME -o OUTPUT -t TEMPLATE [options]")
	opt.add_option("-f", "--file", action="store", type="string",
				   dest="filename",help="Munin datafile to parse")
	opt.add_option("-o", "--output", action="store", type="string",
				   dest="output",help="Nagios config file to generate")
	opt.add_option("-t", "--template", action="append", type="string",
				   dest="templates", help="Nagios template to use. Use format <regex>/template to use this template only of the check matches the regex. The first matching template will be used.")
	opt.add_option("-x", "--excludehost", action="append", type="string",
				   dest="hosts", help="Hosts to exclude. Any hosts matching the specified regexp will have all their checks disabled.")

	(options, args) = opt.parse_args()
	# Chech for mandatory arguments
	if not options.filename:
		print "Use -f to specify Munin datafile."
		opt.print_help()
		sys.exit(1)
	if not options.output:
		print "Use -o to specify Nagios output file."
		opt.print_help()
		sys.exit(1)
	if not options.templates or not len(options.templates):
		print "Use -t to specify one or more templates."
		opt.print_help()
		sys.exit(1)
	if not options.hosts:
		# Turn into empty array so we can iterate over it
		options.hosts = []

	# Convert templates to instances of our classes
	options.templates = [Template(x) for x in options.templates]
	options.hosts = [HostExclude(x) for x in options.hosts]

	# Read the Munin datafile
	f = open(options.filename, "r")
	if not f.readline().startswith("version "):
		print "Invalid header in datafile"
		sys.exit(1)

	# Initialize for looping
	checks = []
	current = Check()

	# For now, read the whole file and sort it (it's not always sorted
	# in the munin output). If the datafile is very large, this could
	# be a problem, but in most cases it should be ok.
	lines = f.readlines()
	f.close()
	for l in sorted(lines):
		# Abort on the first line that doesn't have a semicolon
		# This is a way to avoid some custom variables dumped into the
		# datafile, and focus only on the plugin data.
		# XXX: Would break if there's a plugin with semicolon in the name
		if not l.find(';')>0:
			break
		try:
			if not current.ParseLine(l):
				checks.append(current)
				current = Check()
				current.ParseLine(l)
		except Exception, ex:
			print "Exception parsing line '%s'" % l
			print ex
			sys.exit(1)
	checks.append(current)

	f = open(options.output, "w")
	f.write("\n".join([c.get_nagios_config() for c in checks if c.haslevel]))
	f.close()
