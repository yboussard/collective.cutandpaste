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
__author__= 'yboussard'
__docformat__ = 'restructuredtext'

import os
import time

from zope.event import notify
from zope.interface import classProvides, implements
from zope.annotation.interfaces import IAnnotations
from zope.app.container.contained import ObjectMovedEvent

from transaction import commit
from ZODB.POSException import ConflictError
from OFS.event import ObjectWillBeMovedEvent
from Acquisition import aq_base, aq_inner, aq_parent

from Products.CMFPlone.utils import _createObjectByType
from plone.locking.interfaces import ILockable

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import resolvePackageReferenceOrFile

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
        self.queue = []
        self.waitfor = None
        self.abort = False
        ## for folder that has been created
        self.canfixtranslation = self.options.get('canfixtranslation', False)
        ## juste two lang
        langtranslation = self.options.get('langtranslations', 'fr,en')\
                               .split(',')
        if len(langtranslation) != 2:
            raise Exception('langtranslation option must just define '
                            'two language')
        self.lang1 = langtranslation[0]
        self.lang2 = langtranslation[1]
        self.workflow_transition = self.options.get('workflow_transition',
                                                    'restrict')
        self.fixtranslation = []
        self.location = {}

    def __iter__(self):
        # Before iteration
        # You can do initialisation here
        for item in self.previous:
            # Iteration itself
            # You could process the items, take notes, inject additional
            # items based on the current item in the pipe or manipulate portal
            # content created by previous items
            item['presentindestination'] = False
            item["start"] = time.time()
            item['id'] = item[self.path_src]
            item['newid'] = item[self.path_dst]
            self.location[item['id']] = item['newid']
            self.abort = False
            logger.info('OPERATE <%s>', item['id'])
            if item[self.path_src] != item[self.path_dst]:
                obj = parent = None
                try:
                    obj = self.getObj(item[self.path_src])
                except:
                    ## perhaps parent is move
                    oldlocation = '/'.join(item[self.path_src].split('/')[:-1])
                    idobj = item[self.path_src].split('/')[-1]

                    if self.location.has_key(oldlocation):
                        new_path = '/'.join([self.location[oldlocation],
                                             idobj])
                        item['id'] = new_path
                        try:
                            obj = self.getObj(new_path)
                        except:
                            obj = None
                            item['status'] = 'NotFound Abort'
                    else:
                        item['status'] = 'NotFound Abort'

                ## dst
                if obj and not self.abort:
                    (list_to_create,
                     parent) = self.getCreatedParent(item[self.path_dst])
                    ## first case the parent is none !!!
                    if parent is None:
                        self.abort = True
                        item['status'] = 'Parent NotPresent Abort'
                    if parent:
                        if list_to_create:
                            root = parent
                            parent = self.createTree(parent, list_to_create)
                            if parent is None:
                                self.abort = True
                                item['status'] = 'Parent NotPresent Abort'
                            else:
                                l = []
                                for x in list_to_create:
                                    l.append(x)
                                    ## for LinguaPlone site
                                    self.fixtranslation.append(
                                        '/'.join(list(root.getPhysicalPath()) \
                                                     + l))
                        else:
                            ## parent is good , we verify that destination is
                            ## not present , if it is , we do nothing
                            id = item[self.path_dst].split('/')[-1]
                            if id in parent.objectIds():
                                logger.info('THIS OBJECT IS PRESENT !!')
                                item['presentindestination'] = True
                                item['status'] = 'DestinationPresent Abort'
                                self.abort = True
                ## now cutandpaste
                if not self.abort and parent and obj:
                    self.cutandpaste(obj, parent, item)
            else:
                item['status'] = 'NothingToDo'
            yield item
        # After iteration
        # The section still has control here and could inject additional
        # items, manipulate all portal content created by the pipeline,
        # or clean up after itself.
        # put all translation in csv file
        # for x in self.fixtranslation:
        #     self.writer.writerow(x)
        ## try to fix translation
        ## first reverse translation
        if self.canfixtranslation:

            self.fixtranslation.reverse()
            for x in self.fixtranslation:
                try:
                    obj = self.context.restrictedTraverse(x)\
                          .objectValues()[0].getCanonical()
                    can = obj.aq_parent
                    lang = obj.Language() == self.lang1 and self.lang2 \
                           or self.lang1
                    tr = obj\
                         .getTranslation(lang)\
                         .aq_parent
                    ctr = can.getTranslation(lang)
                    if ctr:
                        if tr == ctr:
                            #do nothing , allready translated
                            pass
                        else:
                            try:
                                ctr.removeTranslationReference(can)
                                tr.addTranslationReference(can)
                            except:
                                logger.exception('problem for fix %s' % x)
                    else:
                        try:
                            tr.addTranslationReference(can)
                        except:
                            logger.exception('problem for fix %s' % x)
                    ## workflow
                    for o in (can, tr):
                        if self.context.portal_workflow\
                               .getInfoFor(o, 'review_state')\
                               == 'private':
                            self.context.portal_workflow.doActionFor(o,
                                                      self.worflow_transition)
                    commit()
                except:
                    logger.exception('problem for fix %s' % x)
                    pass

    def getCreatedParent(self, dst):
        traverser = dst.split('/')
        parent = self.context
        to_create_before = []
        for (i, item) in enumerate(traverser[:-1]):
            if not item:
                continue
            if item in parent.objectIds():
                parent = parent[item]
            else:
                if traverser[i]:
                    to_create_before.append(traverser[i])
        return (to_create_before, parent)

    def getObj(self, dst):
        """ avoid big mistake with restrixted traverse """

        traverser = dst.split('/')
        obj = self.context
        for (i, item) in enumerate(traverser):
            if not item:
                continue
            if item in obj.objectIds():
                obj = obj[item]
            else:
                raise KeyError(item)
        return obj

    def createTree(self, parent, list_to_create):
        try:
            for identifier in list_to_create:
                parent = self.createObject(parent, identifier)
            return parent
        except:
            logger.exception('cant create object %s in %s' % (identifier,
                                     '/'.join(parent.getPhysicalPath())))
            return

    def createObject(self, parent, identifier):
        #create object
        logger.info('create object %s in %s' %
                    (identifier,
                     '/'.join(parent.getPhysicalPath())))

        _createObjectByType(self.content_type, parent, identifier)
        return parent[identifier]

    def cutandpaste(self, obj, parent, item):
        ## unlock object
        ob = obj
        try:
            ILockable(obj).clear_locks()
        except:
            pass
        try:
            id = item[self.path_dst].split('/')[-1]
            orig_id = ob.getId()
            orig_container = aq_parent(aq_inner(ob))
            parent = aq_inner(parent)
            try:
                ob._notifyOfCopyTo(parent, op=1)
            except ConflictError:
                raise
            logger.info('MOVE object in %s/%s TO  %s/%s' \
                            % ('/'.join(orig_container.getPhysicalPath()),
                               orig_id,
                               '/'.join(parent.getPhysicalPath()), id))
            if id in parent.objectIds():
                logger.info('THIS OBJECT IS PRESENT !!')
                item['presentindestination'] = True
                item['status'] = 'DestinationPresent Abort'
                raise Exception('OBJECT is PRESENT')
            notify(ObjectWillBeMovedEvent(ob, orig_container, orig_id,
                                              parent, id))
            ob.manage_changeOwnershipType(explicit=1)
            orig_container._delObject(orig_id, suppress_events=True)
            ob = aq_base(ob)
            ob._setId(id)
            parent._setObject(id, ob, set_owner=0, suppress_events=True)
            ob = parent._getOb(id)
            notify(ObjectMovedEvent(ob, orig_container, orig_id, parent, id))
            ob._postCopy(parent, op=1)
            ob.manage_changeOwnershipType(explicit=0)
            commit()
            item['status'] = 'Ok'
        except:
            logger.exception('CUT PASTE ERROR on %s!!' % item[self.path_src])
            item['status'] = 'CutPasteError'


class CSVSourceSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        filename = resolvePackageReferenceOrFile(options['filename'])
        file_ = open(filename, 'r')
        dialect = options.get('dialect', 'excel')
        fieldnames = options.get('fieldnames')
        delimiter = options.get('delimiter', ',')
        quotechar = options.get('quotechar', '"')
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
        (root, ext) = os.path.splitext(self.file_out)
        filename = "%s-%s%s" % (root, time.strftime('%Y%m%d%H%M%S'), ext)
        self.fieldnames = ['date', 'status', 'time', 'presentindestination',
                           'id', 'newid']
        self.writer = csv.DictWriter(open(filename, "w"),
                                     delimiter= options.get('delimiter', ';'),
                                     fieldnames = self.fieldnames)

    def __iter__(self):
        for item in self.previous:
            item['time'] = time.time() - item['start']
            item['date'] = time.strftime('%c')
            logger.info('%s Status:<%s> Time: %0.2f', item['id'],
                     item.get('status', ''),
                     item['time'])
            d = {}
            for x in self.fieldnames:
                d[x] = item.get(x, '')
            self.writer.writerow(d)
            yield item


class FlushCache(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.every = int(options.get('every', 100))
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
