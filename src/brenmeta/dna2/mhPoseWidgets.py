import traceback

from Qt import QtCore
from Qt import QtWidgets
from Qt import QtGui

from maya import cmds

from brenmeta.core import mhCore
from brenmeta.maya import mhBlendshape

LOG = mhCore.get_basic_logger(__name__)


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

        if isinstance(pose, mhCore.ComboPose):
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

    def __init__(self, combo_mode=False, parent=None):
        super(PoseFilterModel, self).__init__(parent=parent)

        self.ref_poses = None

        self.combo_mode = combo_mode

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
        if self.combo_mode:
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


class PoseWidget(QtWidgets.QWidget):

    SELECTION_CHANGED = QtCore.Signal()

    def __init__(self, combo_mode=False, parent=None):
        super(PoseWidget, self).__init__(parent=parent)

        self._create_widgets(combo_mode=combo_mode)

    def error(self, err):

        print(traceback.format_exc())

        LOG.critical(str(err))

        QtWidgets.QMessageBox.critical(
            self,
            "Error",
            str(err),
            QtWidgets.QMessageBox.Ok
        )

    def set_poses(self, poses):
        self.poses_model.set_poses(poses)

    def set_ref_poses(self, poses):
        self.proxy_model.set_ref_poses(poses)

    def _create_widgets(self, combo_mode=False):
        # type label
        if combo_mode:
            self.type_label = QtWidgets.QLabel("Combo Poses")
        else:
            self.type_label = QtWidgets.QLabel("Poses")

        self.type_label.setAlignment(QtCore.Qt.AlignHCenter)

        # filter
        self.filter_line_edit = QtWidgets.QLineEdit()
        self.filter_line_edit.setFixedHeight(30)
        self.filter_line_edit.textChanged.connect(self.filter_changed)

        self.poses_model = PosesModel()
        self.proxy_model = PoseFilterModel(combo_mode=combo_mode)

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

        self.view.selectionModel().selectionChanged.connect(self._selection_changed)

        # layout
        self.lyt = QtWidgets.QVBoxLayout()
        self.lyt.addWidget(self.type_label)
        self.lyt.addWidget(self.filter_line_edit)
        self.lyt.addWidget(self.view)
        self.lyt.addLayout(self.show_column_lyt)

        self.setLayout(self.lyt)

    def _selection_changed(self):
        self.SELECTION_CHANGED.emit()

    def _show_index_toggled(self):
        self.poses_model.set_show_indices(self.show_index_checkbox.isChecked())

    def _show_pose_toggled(self):
        self.poses_model.set_show_poses(self.show_pose_checkbox.isChecked())

    def _show_shape_toggled(self):
        self.poses_model.set_show_shapes(self.show_shape_checkbox.isChecked())

    def filter_changed(self):
        self.proxy_model.setFilterWildcard(
            "*{}*".format(self.filter_line_edit.text())
        )

    def get_selected_poses(self, warn=False, as_combo=False):
        poses = []

        selection = self.view.selectionModel().selection()

        for proxy_index in selection.indexes():
            index = self.proxy_model.mapToSource(proxy_index)
            pose = self.poses_model.poses[int(index.row())]

            if pose not in poses:
                poses.append(pose)

        if not poses and warn:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No poses selected",
                QtWidgets.QMessageBox.Ok
            )

            return None

        if as_combo:
            combo_pose = mhCore.ComboPose()
            combo_pose.pose = mhCore.Pose()

            for pose in poses:
                if isinstance(pose, mhCore.ComboPose):
                    combo_pose.input_combos.append(pose)
                else:
                    combo_pose.input_poses.append(pose)

            return combo_pose
        else:
            return poses


class PoseEditorWidget(QtWidgets.QFrame):
    def __init__(self, combo_mode=False, parent=None):
        super(PoseEditorWidget, self).__init__(parent=parent)

        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)

        self._poses = None
        self.blendshape_nodes = None

        self.attr_defaults = None
        self._combo_mode = combo_mode

        self._resetting_scene = False
        self._updating_scene = False

        self._create_widgets(combo_mode=combo_mode)

    def error(self, err):

        print(traceback.format_exc())

        LOG.critical(str(err))

        QtWidgets.QMessageBox.critical(
            self,
            "Error",
            str(err),
            QtWidgets.QMessageBox.Ok
        )

    @property
    def poses(self):
        return self._poses

    def set_poses(self, poses):
        self._poses = poses
        self.pose_widget.set_poses(poses)

    def set_ref_poses(self, poses):
        self.pose_widget.set_ref_poses(poses)

    def _create_widgets(self, combo_mode=False):
        # pose widget
        self.pose_widget = PoseWidget(combo_mode=combo_mode)

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

        # TODO match list

        self.match_lyt.addWidget(self.match_mode_combo)
        self.match_lyt.addWidget(self.filter_mode_combo)

        # scene
        self.selected_scene_group_box = QtWidgets.QGroupBox("Scene")
        self.selected_scene_lyt = QtWidgets.QVBoxLayout()
        self.selected_scene_group_box.setLayout(self.selected_scene_lyt)

        self.pose_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pose_slider.valueChanged.connect(self._pose_slider_changed)
        self.pose_slider.setTickInterval(1)
        self.pose_slider.setRange(0, 100)

        self.pose_value_widget = QtWidgets.QDoubleSpinBox()
        self.pose_value_widget.editingFinished.connect(self._pose_value_changed)
        self.pose_value_widget.setDecimals(2)
        self.pose_value_widget.setMinimum(-10.0)
        self.pose_value_widget.setMaximum(10.0)

        self.update_scene_btn = QtWidgets.QPushButton("pose rig")
        self.reset_pose_btn = QtWidgets.QPushButton("reset rig")

        self.update_scene_btn.clicked.connect(self._update_scene_clicked)
        self.reset_pose_btn.clicked.connect(self.reset_scene)

        self.selected_scene_lyt.addWidget(self.pose_slider)
        self.selected_scene_lyt.addWidget(self.pose_value_widget)
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

        if combo_mode:
            self.lyt.addWidget(self.pose_widget)
            self.lyt.addLayout(self.tool_lyt)
        else:
            self.lyt.addLayout(self.tool_lyt)
            self.lyt.addWidget(self.pose_widget)

        self.lyt.setStretchFactor(self.tool_lyt, 0)
        self.lyt.setStretchFactor(self.pose_widget, 1)

        self.setLayout(self.lyt)

    def _match_mode_changed(self):
        mode = MatchMode.items[self.match_mode_combo.currentIndex()]
        self.proxy_model.set_match_mode(mode)

    def _filter_mode_changed(self):
        mode = FilterMode.items[self.filter_mode_combo.currentIndex()]
        self.proxy_model.set_filter_mode(mode)

    def get_selected_poses(self, warn=True, as_combo=False):
        return self.pose_widget.get_selected_poses(warn=True, as_combo=as_combo)

    def reset_scene(self):
        if self._resetting_scene or self._updating_scene:
            return False

        if not self.attr_defaults:
            return False

        self._resetting_scene = True

        try:
            # reset joints to defaults
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

            # reset blendshape targets
            for blendshape_node in self.blendshape_nodes:
                if not cmds.objExists(blendshape_node):
                    continue

                targets = mhBlendshape.get_blendshape_weight_aliases(blendshape_node)

                for target in targets:
                    cmds.setAttr("{}.{}".format(blendshape_node, target), 0.0)

            self.pose_slider.setValue(0)
            self.pose_value_widget.setValue(0.0)

            self._resetting_scene = False
            return True

        except Exception as err:
            self.error(err)
            self._resetting_scene = False
            return False

    def update_scene(self, blend=1.0):
        if self._updating_scene or self._resetting_scene:
            return False

        # get poses
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False

        # reset scene
        reset = self.reset_scene()

        # return if we failed to reset scene
        if not reset:
            return False

        # pose rig
        try:
            self._updating_scene = True

            # pose rig
            pose = self.get_selected_poses(warn=True, as_combo=True)

            pose.pose_joints(blend=blend)
            pose.activate_targets(self.blendshape_nodes, blend=blend)

            # update widgets
            self.pose_slider.setValue(int(blend * 100))
            self.pose_value_widget.setValue(blend)

            self._updating_scene = False

            return True

        except Exception as err:
            self.error(err)
            self._updating_scene = False
            return False

    def _update_scene_clicked(self):
        self.update_scene()

    def _pose_slider_changed(self, value):
        value = value / 100.0
        self.update_scene(blend=value)

    def _pose_value_changed(self):
        value = self.pose_value_widget.value()
        self.update_scene(blend=value)

    def update_data(self):
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False
        else:
            pose = poses[0]

        pose.update_from_scene()

        if isinstance(pose, mhCore.ComboPose):
            LOG.info("Combo pose data updated: {}".format(pose.pose.name))
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
