======================
 changes for uwgroups
======================

0.3.3
=====

* fix error parsing output of openssl

0.3.2
=====

* add 'UWGroups.search_user()' method and corresponding subcommand

0.3.1
=====

* add 'environment' parameter to UWGroups() constructor

0.3.0
=====

* drop python 2.7, support python 3.6+
* use UW groups API v3
  (https://wiki.cac.washington.edu/display/infra/Groups+Service+API+v3)
* use environment variable GWS_HOST to specify API host
* add subcommand 'members'

0.2.5
=====

* Use port 443 instead of 7443

0.2.4
=====

* Better handling of timeout errors.

0.2.3
=====

* add ``timeout`` parameter to ``UWGroups`` constructor and
  ``UWGroups.connect()`` with default of 30s

