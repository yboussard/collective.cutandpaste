# -*- coding: utf-8 -*-
# Copyright (C) 2011 Alterway Solutions 

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING. If not, write to the
# Free Software Foundation, 
# 51 Franklin Street, Suite 500, Boston, MA 02110-1335,USA

"""
$Id:$
"""
__author__  = 'yboussard'
__docformat__ = 'restructuredtext'

import os
import time
from zope.interface import classProvides, implements
from zope.annotation.interfaces import IAnnotations

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
#from collective.transmogrifier.utils import Matcher
#from collective.transmogrifier.utils import defaultMatcher
#from collective.transmogrifier.utils import defaultKeys
from collective.transmogrifier.utils import resolvePackageReferenceOrFile

from Products.CMFPlone.utils import _createObjectByType
from plone.locking.interfaces import ILockable

current_dir = os.path.dirname(__file__)

import logging
import csv

logger = logging.getLogger('collective.cutandpaste')

class CutAndPaste(object):

    classProvides(ISectionBlueprint)
    implements(ISection)
    KEY = 'collective.cutandpaste'

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.path_src = self.options['path_src']
        self.path_dst = self.options['path_dst']
        self.content_type = self.options['content_type']
        
        self.context = transmogrifier.context
        self.request = transmogrifier.context.REQUEST
        self.storage = IAnnotations(transmogrifier).setdefault(self.KEY, {})
        self.stats = 0


    def __iter__(self):
        # Before iteration
        # You can do initialisation here
        
        for item in self.previous:
            # Iteration itself
            # You could process the items, take notes, inject additional
            # items based on the current item in the pipe or manipulate portal
            # content created by previous items
            
            item["start"] = time.time()
            item['id'] = item[self.path_src]
            item['newid'] = ''
            
            if item[self.path_src] != item[self.path_dst]:
                obj = parent = None
                try:
                    obj = self.context.restrictedTraverse(item[self.path_src])
                except:
                    item['status'] = 'NotFound Abort'
                    
                    
                ## dst
                if obj:
                    (list_to_create,
                     parent) = self.getCreatedParent(item[self.path_dst])
                    ## first case the parent is none !!!
                    if parent is None:
                        item['status'] = 'Parent NotPresent Abort'
                    
                    if parent and list_to_create:
                    ## we must create tree before cutandpaste obj
                        logger.info('we create tree %s', list_to_create)
                        parent = self.createTree(parent, list_to_create)
                        if parent is None:
                            item['status'] = 'Cant create tree %s,%s' % (
                                '/'.join(parent.getPhysicalPath()),
                                str(list_to_create))
                        
                ## now cutandpaste
                if parent and obj:
                    self.cutandpaste(obj, parent, item)
                    item['newid'] = item[self.path_dst]
                
            else:
                item['status'] = 'NothingToDo'
            yield item

        # After iteration
        # The section still has control here and could inject additional
        # items, manipulate all portal content created by the pipeline,
        # or clean up after itself.

    def getCreatedParent(self, dst):
        traverser = dst.split('/')
        i = -1
        dst = '/'.join(traverser[:i])
        
        parent = self.context.restrictedTraverse(dst, None)
        
        to_create_before = []
        while parent is None and traverser[:i]:
            to_create_before.append('/'.join(traverser[:i]))
            i -= 1
            dst = '/'.join(traverser[:i])
            parent = self.context.restrictedTraverse(dst, None)
            
        return (to_create_before, parent) 
        
    def createTree(self, parent , list_to_create):

        try:
            
            list_to_create.reverse()
            for x in list_to_create:
                identifier = x.split('/')[-1]
                parent = self.createObject(parent, identifier)
            return parent
        except:
            return 
                
    def createObject(self, parent, identifier):
        #create object
        import pdb;pdb.set_trace();
        logger.info('create object %s in %s' %
                    (identifier,
                     '/'.join(parent.getPhysicalPath())))
        
        _createObjectByType(self.content_type, parent, identifier)
        return parent[identifier]

    def cutandpaste(self, obj, parent, item):
        ## unlock object
        try:
            ILockable(obj).clear_locks()
        except:
            pass
        try:
            
            obj.aq_parent.manage_cutObjects(ids = [obj.id,],
                                                REQUEST = self.request)
        except:
            item['status'] = 'CutError'
        try:
            parent.manage_pasteObjects(REQUEST = self.request)
            item['status'] = 'Ok'
        except:
            item['status'] = 'PasteError'
            
            


class CSVSourceSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        
        filename = resolvePackageReferenceOrFile(options['filename'])
        file_ = open(filename, 'r')
        dialect = options.get('dialect', 'excel')
        fieldnames = options.get('fieldnames')
        delimiter = options.get('delimiter',',')
        quotechar = options.get('quotechar','"')
        if fieldnames:
            fieldnames = fieldnames.split()
        
        self.reader = csv.DictReader(file_, 
                                     dialect=dialect,
                                     fieldnames=fieldnames,
                                     delimiter=delimiter, 
                                     quotechar=quotechar)
    
    def __iter__(self):
        for item in self.previous:
            yield item
        
        for item in self.reader:
            yield item



class Printer(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.file_out = options['file_out']
        self.fieldnames = ['id','newid', 'status','time']
        self.writer = csv.DictWriter(open(self.file_out,"w"),
                                     delimiter= options.get('delimiter',','),
                                     fieldnames = self.fieldnames)
        
        


    def __iter__(self):
        for item in self.previous:
            item['time'] = time.time() - item['start']
            logger.info('%s Status:<%s> Time: %0.2f' , item['id'],
                     item['status'],
                     item['time'])
            d = {}
            for x in self.fieldnames:
                d[x] = item[x]
            self.writer.writerow(d)
            yield item



class FlushCache(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.every = int(options.get('every',100))
        self.cpt = 1
        self.transmogrifier = transmogrifier
        self.context = transmogrifier.context
        self.db = self.context.Control_Panel.Database
        self.database_names = self.db.getDatabaseNames()
        


    def __iter__(self):
        for item in self.previous:
            
            if self.cpt % self.every == 0:
                ## FlushCache
                logger.info('FlushCache')
                [self.db[x]._getDB().cacheMinimize() \
                 for x in self.database_names]
            yield item

