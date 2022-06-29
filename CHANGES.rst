======================
 changes for uwgroups
======================

0.3.6
=====

* Work around error caused by 1024 bit UWCA root cert
  (ssl.SSLError: [SSL: CA_KEY_TOO_SMALL] ca key too small (_ssl.c:2633))

0.3.5
=====

* add batchsize parameter to UWGroups.sync_members()
* change default batchsize to 50

0.3.4
=====

* add subcommands to add and remove users from groups
* recursively create parent groups on group creation

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

