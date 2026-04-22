from Qt import QtCore
from Qt import QtWidgets
from Qt import QtGui

from maya import cmds

from brenmeta.core import mhCore

class PosesModel(QtCore.QAbstractItemModel):
    HEADERS = ["", "pose", "shape"]

    POSE_ROLE = QtCore.Qt.UserRole

    def __init__(self, parent=None):
        super(PosesModel, self).__init__(parent)
        self.poses = None

        self.show_indices = True
        self.show_poses = True
        self.show_shapes = True

    def set_poses(self, poses):
        self.beginResetModel()
        self.poses = poses
        self.endResetModel()

    def set_show_indices(self, value):
        self.beginResetModel()
        self.show_indices = value
        self.endResetModel()

    def set_show_poses(self, value):
        self.beginResetModel()
        self.show_poses = value
        self.endResetModel()

    def set_show_shapes(self, value):
        self.beginResetModel()
        self.show_shapes = value
        self.endResetModel()

    def get_columns(self):
        columns = []

        if self.show_indices:
            columns.append(self.HEADERS[0])
        if self.show_poses:
            columns.append(self.HEADERS[1])
        if self.show_shapes:
            columns.append(self.HEADERS[2])

        return columns

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.get_columns())

    def headerData(self, section, orientation, role):
        headers = self.get_columns()

        if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
            if orientation == QtCore.Qt.Horizontal:
                if section < len(headers):
                    return headers[section]

        return super(PosesModel, self).headerData(section, orientation, role)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not self.poses:
            return 0

        if parent.isValid():
            return 0
        else:
            return len(self.poses)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not self.poses:
            return None

        pose = index.internalPointer()

        if role is self.POSE_ROLE:
            return pose

        if isinstance(pose, mhCore.PSDPose):
            pose = pose.pose

        if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
            column_data = []

            if self.show_indices:
                column_data.append(pose.index)
            if self.show_poses:
                column_data.append(pose.name)
            if self.show_shapes:
                column_data.append(pose.shape_name)

            if index.column() < len(column_data):
                return column_data[index.column()]
            else:
                return None

        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid() or not self.poses:
            return None

        pose = index.internalPointer()

        if role == QtCore.Qt.EditRole:
            if index.column() == 0:
                # TODO?
                return False

        return False

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.poses:
            return QtCore.QModelIndex()

        if parent.isValid():
            return QtCore.QModelIndex()

        return self.createIndex(row, column, self.poses[row])

    def parent(self, index):
        return QtCore.QModelIndex()

    def flags(self, index):
        if not self.poses:
            return QtCore.Qt.NoItemFlags

        flags = QtCore.Qt.ItemFlags()

        # set as appropriate
        flags = flags | QtCore.Qt.ItemIsEnabled
        flags = flags | QtCore.Qt.ItemIsSelectable

        return flags

class MatchMode:
    class Any:
        name = "any"

    class All:
        name = "all"

    class Exact:
        name = "exact"

    items = [Any, All, Exact]


class FilterMode:
    class NoFilter:
        name = "none"

    class Highlight:
        name = "highlight"

    class Isolate:
        name = "isolate"

    items = [NoFilter, Highlight, Isolate]


class PoseFilterModel(QtCore.QSortFilterProxyModel):
    """
    """

    HIGHLIGHT_COLOR = QtGui.QColor(0, 100, 0)

    def __init__(self, psd_mode=False, parent=None):
        super(PoseFilterModel, self).__init__(parent=parent)

        self.ref_poses = None

        self.psd_mode = psd_mode

        self._match_mode = MatchMode.Any
        self._filter_mode = FilterMode.Highlight


    def set_ref_poses(self, poses):
        self.beginResetModel()
        self.ref_poses = poses
        self.endResetModel()

    @property
    def match_mode(self):
        return self._match_mode

    def set_match_mode(self, value):
        self.beginResetModel()
        self._match_mode = value
        self.endResetModel()

    @property
    def filter_mode(self):
        return self._filter_mode

    def set_filter_mode(self, value):
        self.beginResetModel()
        self._filter_mode = value
        self.endResetModel()

    def ref_pose_match(self, pose):
        if self.psd_mode:
            matches = [ref_pose in pose.input_poses for ref_pose in self.ref_poses]

            if self.match_mode is MatchMode.Exact:
                return all(matches) and len(matches) == len(pose.input_poses)
        else:
            matches = [pose in ref_pose.input_poses for ref_pose in self.ref_poses]

            # TODO?
            if self.match_mode is MatchMode.Exact:
                return all(matches)

        if self.match_mode is MatchMode.Any:
            return any(matches)

        elif self.match_mode is MatchMode.All:
            return all(matches)

        # elif self.match_mode is MatchMode.Exact:
        #     return all(matches) and len(matches) == len(ref_poses)
        else:
            raise mhCore.MHError("Filter mode not recognised: {}".format(self.match_mode))

    def data(self, index, role):
        """Override source model data method.

        Add background colour for highlighted indices.
        """

        if not index.isValid():
            return None

        if role == QtCore.Qt.BackgroundRole:
            if not self.ref_poses:
                return None

            if self.filter_mode is not FilterMode.Highlight:
                return None

            source_index = self.mapToSource(index)

            pose = self.sourceModel().data(source_index, PosesModel.POSE_ROLE)

            if self.ref_pose_match(pose):
                return self.HIGHLIGHT_COLOR
            else:
                return None

        return super(PoseFilterModel, self).data(index, role)

    def filterAcceptsRow(self, source_row, source_parent):
        if source_parent.isValid():
            return False

        if self.filter_mode is FilterMode.Isolate:
            # index = self.sourceModel().index(source_row, 0, parent=source_parent)
            # pose = self.data(index, PosesModel.POSE_ROLE)
            pose = self.sourceModel().poses[source_row]
            return self.ref_pose_match(pose)

        return super(PoseFilterModel, self).filterAcceptsRow(source_row, source_parent)


class PoseEditorWidget(QtWidgets.QFrame):
    def __init__(self, name, psd_mode=False, parent=None):
        super(PoseEditorWidget, self).__init__(parent=parent)

        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)

        self._poses = None
        self.attr_defaults = None
        self._psd_mode = psd_mode
        self._create_widgets(psd_mode=psd_mode)

    @property
    def poses(self):
        return self._poses

    def set_poses(self, poses):
        self._poses = poses
        self.poses_model.set_poses(poses)

    def _create_widgets(self, psd_mode=False):

        # type label
        if psd_mode:
            self.type_label = QtWidgets.QLabel("PSD Poses")
        else:
            self.type_label = QtWidgets.QLabel("Poses")

        self.type_label.setAlignment(QtCore.Qt.AlignHCenter)

        # filter
        self.filter_line_edit = QtWidgets.QLineEdit()
        self.filter_line_edit.setFixedHeight(30)
        self.filter_line_edit.textChanged.connect(self.filter_changed)

        self.poses_model = PosesModel()
        self.proxy_model = PoseFilterModel(psd_mode=psd_mode)

        # if psd_mode:
        #     self.proxy_model = PoseFilterModel()
        # else:
        #     self.proxy_model = QtCore.QSortFilterProxyModel()

        self.proxy_model.setSourceModel(self.poses_model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)

        # column checkboxes
        self.show_index_checkbox = QtWidgets.QCheckBox("index")
        self.show_pose_checkbox = QtWidgets.QCheckBox("pose")
        self.show_shape_checkbox = QtWidgets.QCheckBox("shape")

        self.show_index_checkbox.setChecked(True)
        self.show_pose_checkbox.setChecked(True)
        self.show_shape_checkbox.setChecked(True)

        self.show_index_checkbox.toggled.connect(self._show_index_toggled)
        self.show_pose_checkbox.toggled.connect(self._show_pose_toggled)
        self.show_shape_checkbox.toggled.connect(self._show_shape_toggled)

        self.show_column_lyt = QtWidgets.QHBoxLayout()

        self.show_column_lyt.addWidget(self.show_index_checkbox)
        self.show_column_lyt.addWidget(self.show_pose_checkbox)
        self.show_column_lyt.addWidget(self.show_shape_checkbox)

        # view
        self.view = QtWidgets.QTreeView()
        self.view.setModel(self.proxy_model)
        self.view.setSelectionMode(QtWidgets.QTreeView.SelectionMode.ExtendedSelection)
        self.view.header().resizeSection(0, 50)
        self.view.header().resizeSection(1, 150)

        self.view_lyt = QtWidgets.QVBoxLayout()
        self.view_lyt.addWidget(self.type_label)
        self.view_lyt.addWidget(self.filter_line_edit)
        self.view_lyt.addWidget(self.view)
        self.view_lyt.addLayout(self.show_column_lyt)

        # match options
        self.match_group_box = QtWidgets.QGroupBox("Match")
        self.match_lyt = QtWidgets.QVBoxLayout()
        self.match_group_box.setLayout(self.match_lyt)

        self.match_mode_combo = QtWidgets.QComboBox()
        self.match_mode_combo.addItems([item.name for item in MatchMode.items])
        self.match_mode_combo.currentIndexChanged.connect(self._match_mode_changed)

        self.filter_mode_combo = QtWidgets.QComboBox()
        self.filter_mode_combo.addItems([item.name for item in FilterMode.items])
        self.filter_mode_combo.setCurrentIndex(1)
        self.filter_mode_combo.currentIndexChanged.connect(self._filter_mode_changed)

        self.match_lyt.addWidget(self.match_mode_combo)
        self.match_lyt.addWidget(self.filter_mode_combo)

        # scene
        self.selected_scene_group_box = QtWidgets.QGroupBox("Scene")
        self.selected_scene_lyt = QtWidgets.QVBoxLayout()
        self.selected_scene_group_box.setLayout(self.selected_scene_lyt)

        self.update_scene_btn = QtWidgets.QPushButton("pose joints")
        self.reset_pose_btn = QtWidgets.QPushButton("reset joints")

        self.update_scene_btn.clicked.connect(self.update_scene)
        self.reset_pose_btn.clicked.connect(self.reset_scene)

        self.selected_scene_lyt.addWidget(self.update_scene_btn)
        self.selected_scene_lyt.addWidget(self.reset_pose_btn)

        # data
        self.selected_data_group_box = QtWidgets.QGroupBox("Data")
        self.selected_data_lyt = QtWidgets.QVBoxLayout()
        self.selected_data_group_box.setLayout(self.selected_data_lyt)

        self.update_sl_btn = QtWidgets.QPushButton("update pose")
        self.mirror_sl_btn = QtWidgets.QPushButton("mirror")
        self.scale_sl_btn = QtWidgets.QPushButton("scale")
        self.scale_sl_ipv_btn = QtWidgets.QPushButton("scale IPV")

        self.update_sl_btn.clicked.connect(self.update_data)
        self.mirror_sl_btn.clicked.connect(self.mirror_pose)
        self.scale_sl_btn.clicked.connect(self.scale_pose)
        self.scale_sl_ipv_btn.clicked.connect(self.scale_pose_ipv)

        self.selected_data_lyt.addWidget(self.update_sl_btn)
        self.selected_data_lyt.addWidget(self.mirror_sl_btn)
        self.selected_data_lyt.addWidget(self.scale_sl_btn)
        self.selected_data_lyt.addWidget(self.scale_sl_ipv_btn)

        # tool layout
        self.tool_lyt = QtWidgets.QVBoxLayout()

        self.tool_lyt.addWidget(self.match_group_box)
        self.tool_lyt.addWidget(self.selected_scene_group_box)
        self.tool_lyt.addWidget(self.selected_data_group_box)
        self.tool_lyt.addStretch()

        # main layout
        self.lyt = QtWidgets.QHBoxLayout()

        if psd_mode:
            self.lyt.addLayout(self.view_lyt)
            self.lyt.addLayout(self.tool_lyt)
        else:
            self.lyt.addLayout(self.tool_lyt)
            self.lyt.addLayout(self.view_lyt)

        self.setLayout(self.lyt)

    def _show_index_toggled(self):
        self.poses_model.set_show_indices(self.show_index_checkbox.isChecked())

    def _show_pose_toggled(self):
        self.poses_model.set_show_poses(self.show_pose_checkbox.isChecked())

    def _show_shape_toggled(self):
        self.poses_model.set_show_shapes(self.show_shape_checkbox.isChecked())

    def _match_mode_changed(self):
        mode = MatchMode.items[self.match_mode_combo.currentIndex()]
        self.proxy_model.set_match_mode(mode)

    def _filter_mode_changed(self):
        mode = FilterMode.items[self.filter_mode_combo.currentIndex()]
        self.proxy_model.set_filter_mode(mode)

    def filter_changed(self):
        self.proxy_model.setFilterWildcard(
            "*{}*".format(self.filter_line_edit.text())
        )

    def get_selected_poses(self, warn=False):
        poses = []

        selection = self.view.selectionModel().selection()

        for proxy_index in selection.indexes():
            index = self.proxy_model.mapToSource(proxy_index)
            pose = self.poses[int(index.row())]

            if pose not in poses:
                poses.append(pose)

        if not poses and warn:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No poses selected",
                QtWidgets.QMessageBox.Ok
            )

        return poses

    # def reset_scene(self):
    #     mhJoints.reset_scene_joint_xforms(self.calib_reader)

    def reset_scene(self):
        for attr, value in self.attr_defaults.items():
            if not cmds.objExists(attr):
                continue

            if value is None:
                continue

            try:
                cmds.setAttr(attr, value)
            except RuntimeError as err:
                LOG.warning("failed to reset joint attr: {}".format(attr))
                continue

        return True

    def update_scene(self):
        self.reset_scene()

        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False

        print(poses)

        if len(poses) > 1:
            summed_pose = mhCore.Pose()

            for pose in poses:
                summed_pose += pose
        else:
            summed_pose = poses[0]

        summed_pose.pose_joints()

        return True

    def update_data(self):
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False
        else:
            pose = poses[0]

        pose.update_from_scene()

        if isinstance(pose, mhCore.PSDPose):
            LOG.info("PSD pose data updated: {}".format(pose.pose.name))
        else:
            LOG.info("pose data updated: {}".format(pose.name))

        return True

    def mirror_pose(self):
        QtWidgets.QMessageBox.warning(
            self,
            "Warning",
            "Mirror pose not yet implemented",
            QtWidgets.QMessageBox.Ok
        )

    def scale_pose(self):
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False

        scale_value, ok = QtWidgets.QInputDialog.getDouble(
            self, "Scale pose(s)", "Value to scale translate values of selected poses:",
            value=1.0, min=0.0, max=10000, decimals=3
        )

        if not ok:
            return False

        scale_value = float(scale_value)

        for pose in poses:
            pose.scale_deltas(scale_value)

        return True

    def scale_pose_ipv(self):
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False

        scale_value, ok = QtWidgets.QInputDialog.getDouble(
            self, "Scale IPV pose(s)", "Value to scale translate values of selected poses\nOn IPV joints only:",
            value=1.0, min=0.0, max=10000, decimals=3
        )

        if not ok:
            return False

        scale_value = float(scale_value)

        ipv_joints = cmds.ls("*IPV*", type="joint")

        for pose in poses:
            pose.scale_deltas(scale_value, joints=ipv_joints)

        return True
