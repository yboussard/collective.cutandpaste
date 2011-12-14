collective.cutandpaste Package Readme
=====================================

Overview
--------

for copy and paste items for plone with an csv file
csv file must have a minimun of two columns: src path and the dst path

it's looks like that ::

  src;dst
  dir/sdir;dir2/sdir1
  dir/sdir/ssdir1;dir2/sdir2
  dir/sdir/ssdir2;dir2/sdir3

The result must be :

 - directory sdir is moved to dir2 and rename sdir1
 - directory ssdir1 is moved to dir2 and rename sdir2
 - directory ssdir2 is moved to dir2 and rename sdir3


Use
---

This tool use transmogrifier. Please refer to transmogrifier documentation in order to know how it work.
You define copy and paste operation via an transmogrifier cfg configuration file name cutandpaste.cfg (on collective.cutandpaste/collective/cutandpaste/cutandpaste.cfg)

To launch the cut and paste process:

  1 - go to portal_setup (zmi)

  2 - select collective.cutandpaste

  3 - check transmogrifier step

  4 - click to "Import selected steps" button

Blueprint
---------

This package define some blueprints :

collective.cutandpaste.csvreader
++++++++++++++++++++++++++++++++

Read an csv file (source section for transmogrifier): as collective.transmogrifier one but you can define delimiter.

collective.cutandpaste.main
+++++++++++++++++++++++++++

Cut and paste process

options :

 - path_src : the name of key for the src path
 - path_dst : the name of dst for the dst path
 - content_type : ATFolder (if dst path is not exists, the collective.cutandpaste.main create destination parent path for you)


collective.cutandpaste.flushcache
+++++++++++++++++++++++++++++++++

Flush zodb cache (for keeping memory low)

options :

 - every : flush cache every iterate (default 100)

collective.cutandpaste.printer
++++++++++++++++++++++++++++++

define an csv file for output reports

options :

 - file_out : path of the csv file fout output
 - delimiter : the delimiter



