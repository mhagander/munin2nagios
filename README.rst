Munin2Nagios
============
Munin2Nagios consists of two simple scripts, `munin2nagios.py` and
`munin_nag.py` that are used in place of the built-in Nagios integration
in Munin.

The built-in Nagios integration in Munin requires that each plugin is
registered manually in Nagios - something which defeats the point of
Munins automatic node-driven configuration. The script `munin2nagios`
is used to automate this - it will read the `datafile` output from
Munin, and turn this into a Nagios configuration file listing those
plugins that have warning and/or critical levels set.

A second issue integrating Munin and Nagios, is that Munin allows
many more characters in plugin names (or rather, `graph_title`:s)
than Nagios allows in it's plugin names. For this reason,
`munin2nagios` will normalize the plugin names into something that
can be read by Nagios. To make the alerts work, this also requires
the use of `munin_nag.py` to send the alerts into Nagios, since the
names need to be normalized the same way there.

munin2nagios.py
---------------
`munin2nagios.py` is designed to run from cron at regular intervals,
and will generate a nagios configuration output. Some extenral script
should detect if this configuration has changed, and reload the nagios
configuration if necessary - this part is not included.

`munin2nagios.py` will generate a Nagios configuration that uses
named templates. The general Nagios configuration should already contain
the definition of these templates. Using different templates for
different plugins is also supported using regular expression matching.

Commandline arguments
+++++++++++++++++++++
`munin2nagios.py` is controlled from the commandline::

	Usage: munin2nagios.py -f FILENAME -o OUTPUT -t TEMPLATE [options]
	Options:
	  -h, --help            show this help message and exit
	  -f FILENAME, --file=FILENAME
	                        Munin datafile to parse
	  -o OUTPUT, --output=OUTPUT
	                        Nagios config file to generate
	  -t TEMPLATES, --template=TEMPLATES
	                        Nagios template to use. Use format <regex>/template to
	                        use this template only of the check matches the regex.
	                        The first matching template will be used.
	  -x HOSTS, --excludehost=HOSTS
	                        Hosts to exclude. Any hosts matching the specified
	                        regexp will have all their checks disabled.
	  -z, --flatten         Flatten hostnames by removing the domain part

A typical example will look something like this::

	munin2nagios.py -f /usr/local/munin/var/rrd/datafile -o /tmp/munin_auto.cfg -t ".*eth0/" -t "df/munindiskservice" -t muninservice
	cmp -s /tmp/munin_auto.cfg /usr/local/nagios/etc/munin_auto.cfg
	if [ "$?" != "0" ]; then
	   cp /tmp/munin_auto.cfg /usr/local/nagios/etc/munin_auto.cfg
	   /etc/init.d/nagios restart
	fi

This will read the Munin datafile from a local install, and write the generated
Nagios config to /tmp, copying it into the main Nagios configuration and
restarting Nagios if necessary. The template matching performs the following
steps:

 * If the plugin name matches the regexp ".*eth0", that plugin is **excluded**.
   It will show up in the Nagios configuration as commented out. Any alerts
   submitted on it will be ignored by Nagios.
 * If the plugin name matches the regexp "df", it will use the Nagios service
   template "munindiskservice", with whatever paremeters are defined in it.
 * For all other plugins, the Nagios service template "muninservice" will be
   used.

Nagios templates
++++++++++++++++
Nagios templates need to include the definitions required for passive
service checks. A typical Nagios template can look something like this::

	define service {
	        name                    muninservice
	        active_checks_enabled   0
	        passive_checks_enabled  1
	        notifications_enabled   1
	        event_handler_enabled   1
	        use                     baseservice
	        check_command           dummy!0
	        register                0
	}

Where `base_service` contains the installations standard settings for
notification and such things. For this, the command dummy is needed if
it's not already defined - use something like::

	define command{
	        command_name    dummy
	        command_line    /bin/false
	}

Hostname flattening
+++++++++++++++++++
`munin2nagios.py` can be given the commandline option `-z` to make it flatten
all hostnames by removing their domain name. Munin always works with the
FQDN of the host, whereas Nagios often works with just the hostname - this
allows mapping between them. Note that if `-z` is used in `munin2nagios.py`,
it must also be enabled in `munin_nag.py`.

munin_nag.py
------------
The `munin_nag.py` script is the one that translates and sends the alerts
from Munin into Nagios. Configure it in your `munin.cfg` along the lines
of::

	contact.nag.command /usr/local/munin2nagios/munin_nag.py /usr/local/nagios/var/rw/nagios.cmd "${var:host}" "${var:graph_title}"
	contact.nag.always_send warning critical

The Munin user must also be given write permissions to `nagios.cmd` to be
able to send the alergs into Nagios.

Hostname flattening
+++++++++++++++++++
`munin_nag.py` takes an optional parameter `-z` to make it do hostname
flattening, just like `nagios2munin.py`. If this parameter is used on one
of the commands, it must be used on the other one as well.
