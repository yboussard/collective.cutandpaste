collective.cutandpaste Package Readme
=====================================

Overview
--------

for copy and paste items for plone with an csv file
csv file must have a minimun of two columns: src path and the dst path

it's looks like that ::
 
  src;dst
  panels/dossier-en;panels2/dossier-en 
  panels2/dossier;panels/dossier
  panels/dossier;panels/panels3/dossier
  panels2/dossier-en;panels/panels4/souspanels4/dossier-en 
  
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
 


