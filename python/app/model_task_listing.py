# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from collections import defaultdict
from sgtk.platform.qt import QtCore, QtGui

import sgtk
from . import utils

from .model_entity_listing import SgEntityListingModel

# import the shotgun_model module from the shotgun utils framework
shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_model")
ShotgunModel = shotgun_model.ShotgunModel


class SgTaskListingModel(SgEntityListingModel):
    """
    Model to list tasks
    """
    
    data_updated = QtCore.Signal()

    def __init__(self, entity_type, parent):
        """
        Model which represents the latest publishes for an entity
        """
        # init base class
        SgEntityListingModel.__init__(self, entity_type, parent)
        self.data_refreshed.connect(self._on_data_refreshed)
        
        # have a model to pull down user's thumbnails for task assingments
        self._task_assignee_model = TaskAssigneeModel(self)
        self._task_assignee_model.thumbnail_updated.connect(self._on_user_thumb)
        
    ############################################################################################
    # public interface
  
    def _on_data_refreshed(self):
        """
        helper method. dispatches the after-refresh signal
        so that a data_updated signal is consistenntly sent
        out both after the data has been updated and after a cache has been read in
        """
        self.data_updated.emit()
  
    def _on_user_thumb(self, sg_data, image):

        rows = self.rowCount()
        
        for x in range(rows):
            item = self.item(x)
            data = item.get_sg_data()
            user_ids = [x["id"] for x in data["task_assignees"]]
            if sg_data["id"] in user_ids:
                # this thumbnail should be assigned
                print sg_data
                icon = self._sg_formatter.create_thumbnail(image, sg_data)
                item.setIcon(QtGui.QIcon(icon))

        
  
    def _populate_default_thumbnail(self, item):
        """
        Called whenever an item needs to get a default thumbnail attached to a node.
        When thumbnails are loaded, this will be called first, when an object is
        either created from scratch or when it has been loaded from a cache, then later
        on a call to _populate_thumbnail will follow where the subclassing implementation
        can populate the real image.
        """
        if self._sg_location.entity_type == "HumanUser":
            # TODO - refactor this into a nicer piece of code
            item.setIcon(self._sg_formatter._rect_default_icon) 
        else:
            item.setIcon(self._sg_formatter._round_default_icon)
            
 
    def _populate_thumbnail_image(self, item, field, image, path):
        """
        Called whenever a thumbnail for an item has arrived on disk. In the case of
        an already cached thumbnail, this may be called very soon after data has been
        loaded, in cases when the thumbs are downloaded from Shotgun, it may happen later.
 
        This method will be called only if the model has been instantiated with the
        download_thumbs flag set to be true. It will be called for items which are
        associated with shotgun entities (in a tree data layout, this is typically
        leaf nodes).
 
        This method makes it possible to control how the thumbnail is applied and associated
        with the item. The default implementation will simply set the thumbnail to be icon
        of the item, but this can be altered by subclassing this method.
 
        Any thumbnails requested via the _request_thumbnail_download() method will also
        resurface via this callback method.
 
        :param item: QStandardItem which is associated with the given thumbnail
        :param field: The Shotgun field which the thumbnail is associated with.
        :param path: A path on disk to the thumbnail. This is a file in jpeg format.
        """        
        if field != self._sg_formatter.thumbnail_field: 
            # there may be other thumbnails being loaded in as part of the data flow
            # (in particular, created_by.HumanUser.image) - these ones we just want to 
            # ignore and not display.
            return
         
        if self._sg_location.entity_type == "HumanUser":
            # only show square thumbs for users
            sg_data = item.get_sg_data()
            icon = self._sg_formatter.create_thumbnail(image, sg_data)
            item.setIcon(QtGui.QIcon(icon))


    def get_user_ids(self):
        """
        Returns the sg data dictionary for the associated item
        None if not available.
        """
        rows = self.rowCount()
        
        # get the task assignees
        assignees = []
        for x in range(rows):
            data = self.item(x).get_sg_data()
            assignees.extend(data["task_assignees"])
        
        return [x["id"] for x in assignees] 





class TaskAssigneeModel(ShotgunModel):
    """
    Model that caches data about the current user
    """
    # signals
    thumbnail_updated = QtCore.Signal(dict, QtGui.QImage)

    def __init__(self, parent):
        """
        Constructor
        """
        # init base class
        ShotgunModel.__init__(self, parent, bg_load_thumbs=True)
        self._app = sgtk.platform.current_bundle()
        self._task_model = parent
        self._task_model.data_updated.connect(self._load_user_thumbnails)

    def _load_user_thumbnails(self):
        
        user_ids = self._task_model.get_user_ids()
        
        fields = ["image"]
        self._load_data("HumanUser", [["id", "in", user_ids]], ["id"], fields)    
        self._refresh_data()
        

    def _populate_thumbnail_image(self, item, field, image, path):
        """
        Called whenever a thumbnail for an item has arrived on disk. In the case of
        an already cached thumbnail, this may be called very soon after data has been
        loaded, in cases when the thumbs are downloaded from Shotgun, it may happen later.

        This method will be called only if the model has been instantiated with the
        download_thumbs flag set to be true. It will be called for items which are
        associated with shotgun entities (in a tree data layout, this is typically
        leaf nodes).

        This method makes it possible to control how the thumbnail is applied and associated
        with the item. The default implementation will simply set the thumbnail to be icon
        of the item, but this can be altered by subclassing this method.

        Any thumbnails requested via the _request_thumbnail_download() method will also
        resurface via this callback method.

        :param item: QStandardItem which is associated with the given thumbnail
        :param field: The Shotgun field which the thumbnail is associated with.
        :param path: A path on disk to the thumbnail. This is a file in jpeg format.
        """        
        self._current_pixmap = utils.create_round_thumbnail(image)
        sg_data = item.get_sg_data()
        self.thumbnail_updated.emit(sg_data, image)