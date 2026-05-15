# brenmeta metahuman DNA modification tool
#
# Copyright (C) 2025 Brenainn Jordan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""

"""
from typing import Any

import os
import traceback

from maya import cmds
from maya import OpenMayaUI
from maya.api import OpenMaya

from Qt import QtCore
from Qt import QtWidgets
from Qt import QtGui

from brenmeta.core import mhProject

try:
    from shiboken2 import wrapInstance  # Maya with PySide2
except ImportError:
    from shiboken6 import wrapInstance  # Maya with PySide6

import dna
import dnacalib2
import mh_character_assembler

from mh_assemble_lib.model.dnalib import DNAReader, Layer

from brenmeta.core import mhCore
from brenmeta.core import mhWidgets
from brenmeta.dna2 import mhSrc
from brenmeta.dna2 import mhUtils
from brenmeta.dna2 import mhBehaviour
# from brenmeta.dna1 import mhUeUtils
from brenmeta.dna2 import mhMesh
from brenmeta.dna2 import mhJoints
from brenmeta.dna2 import mhPoseWidgets
from brenmeta.mh import mhFaceMaterials
from brenmeta.mh import mhFaceJoints
from brenmeta.mh import mhFaceMeshes
from brenmeta.maya import mhAnimUtils
from brenmeta.maya import mhMayaUtils
from brenmeta.maya import mhBakeRig
from brenmeta.maya import mhBlendshape

LOG = mhCore.get_basic_logger(__name__)

DEFAULT_DNA_DATA_DIR = mhSrc.get_dna_data_dir()


class ProjectWidget(mhWidgets.Tab):
    PATHS_CHANGED = QtCore.Signal()

    def __init__(self, project, parent=None):
        super().__init__(project, parent=parent)

        self.is_refreshing = False

        lyt = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(lyt)

        self.dna_assets_dir_widget = mhWidgets.DirWidget("Dna Assets Dir")

        self.input_file_widget = mhWidgets.PathOpenWidget("Input DNA")
        self.input_file_widget.filter = "dna files (*.dna)"

        self.output_file_widget = mhWidgets.PathSaveWidget("Output DNA")
        self.output_file_widget.filter = "dna files (*.dna)"

        self.bake_config_file_widget = mhWidgets.PathOpenWidget("bake config")
        self.bake_config_file_widget.filter = "json files (*.json)"

        self.dna_assets_dir_widget.PATH_CHANGED.connect(self.paths_changed)
        self.input_file_widget.PATH_CHANGED.connect(self.paths_changed)
        self.output_file_widget.PATH_CHANGED.connect(self.paths_changed)
        self.bake_config_file_widget.PATH_CHANGED.connect(self.paths_changed)

        lyt.addWidget(self.dna_assets_dir_widget)
        lyt.addWidget(self.input_file_widget)
        lyt.addWidget(self.output_file_widget)
        lyt.addWidget(self.bake_config_file_widget)
        lyt.addStretch()

    def paths_changed(self):
        if self.is_refreshing:
            return True

        self.project.dna_assets_path = self.dna_assets_dir_widget.path
        self.project.input_dna_path = self.input_file_widget.path
        self.project.output_dna_path = self.output_file_widget.path
        self.project.bake_config_path = self.bake_config_file_widget.path

        self.PATHS_CHANGED.emit()

        return True

    def refresh(self):
        self.is_refreshing = True

        self.dna_assets_dir_widget.path = self.project.dna_assets_path
        self.input_file_widget.path = self.project.input_dna_path
        self.output_file_widget.path = self.project.output_dna_path
        self.bake_config_file_widget.path = self.project.bake_config_path

        self.is_refreshing = False


class DnaTransferWidget(mhWidgets.Tab):
    class UtilsMenu(QtWidgets.QMenu):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.setTitle("utils")

            empty_icon = QtGui.QIcon()

            self.eyewet_post_action = QtWidgets.QAction(empty_icon, 'eyewet post', self)
            self.eyewet_post_action.setStatusTip('run post-process on eye wet meshes')
            self.addAction(self.eyewet_post_action)

            self.wrap_meshes_action = QtWidgets.QAction(empty_icon, 'create eyelid wrap meshes', self)
            self.wrap_meshes_action.setStatusTip('create proxy meshes for wrapping eye geo')
            self.addAction(self.wrap_meshes_action)

    def __init__(self, project, parent=None):
        super(DnaTransferWidget, self).__init__(project, parent=parent)

        self._create_menus()
        self._create_widgets()

    def _create_menus(self):
        # menu
        self.menubar = self.menuBar()

        self.utils_menu = self.UtilsMenu(parent=self)
        self.menubar.addMenu(self.utils_menu)

        self.utils_menu.eyewet_post_action.triggered.connect(self._eyewet_post_clicked)
        self.utils_menu.wrap_meshes_action.triggered.connect(self._create_eyelid_wrap_meshes_clicked)

    def _create_widgets(self):
        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # transfer meshes
        self.transfer_meshes_widget = QtWidgets.QWidget()

        meshes_lyt = QtWidgets.QVBoxLayout()
        self.transfer_meshes_widget.setLayout(meshes_lyt)

        self.prefix_label = QtWidgets.QLabel(
            "This process will transfer the eye and inner mouth meshes to a new face mesh.\n\n"
            "First add 'src' prefix to all meshes, then import your new head mesh\n\n"
            "Check which meshes to transfer, then click the button!\n"
        )

        self.prefix_meshes_btn = QtWidgets.QPushButton("add src prefix")
        self.prefix_meshes_btn.clicked.connect(self.prefix_meshes)

        meshes_lyt.addWidget(self.prefix_label)
        meshes_lyt.addWidget(self.prefix_meshes_btn)

        # TODO more options
        self.eyeballs_checkbox = QtWidgets.QCheckBox("eyeballs")
        self.eyelashes_checkbox = QtWidgets.QCheckBox("eyelashes")
        self.eyewet_checkbox = QtWidgets.QCheckBox("eyewet")
        self.inner_mouth_checkbox = QtWidgets.QCheckBox("inner mouth")
        self.cleanup_checkbox = QtWidgets.QCheckBox("cleanup")

        for checkbox in [
            self.eyeballs_checkbox,
            self.eyelashes_checkbox,
            self.eyewet_checkbox,
            self.inner_mouth_checkbox,
            self.cleanup_checkbox,
        ]:
            checkbox.setChecked(True)
            # checkbox.setFixedWidth(80)
            meshes_lyt.addWidget(checkbox)

        self.transfer_face_meshes_btn = QtWidgets.QPushButton("transfer face meshes")
        self.transfer_face_meshes_btn.clicked.connect(self.transfer_face_meshes)

        meshes_lyt.addWidget(self.transfer_face_meshes_btn)
        meshes_lyt.addStretch()

        # transfer joints
        self.transfer_joints_widget = QtWidgets.QWidget()

        joints_lyt = QtWidgets.QVBoxLayout()
        self.transfer_joints_widget.setLayout(joints_lyt)

        self.joints_label = QtWidgets.QLabel(
            "This process will align all joints to the new meshes.\n\n"
            "Please ensure meshes below match the meshes in the scene\n\n"
            "Un-check any regions you do not wish to align\n"
        )

        joints_lyt.addWidget(self.joints_label)

        self.head = mhWidgets.DnaTransferMeshWidget("Head", "src_head_lod0_mesh", "head_lod0_mesh")
        self.teeth = mhWidgets.DnaTransferMeshWidget("Teeth", "src_teeth_lod0_mesh", "teeth_lod0_mesh")
        self.left_eye = mhWidgets.DnaTransferMeshWidget("Left Eye", "src_eyeLeft_lod0_mesh", "eyeLeft_lod0_mesh")
        self.right_eye = mhWidgets.DnaTransferMeshWidget("Right Eye", "src_eyeRight_lod0_mesh", "eyeRight_lod0_mesh")

        self.neck_checkbox = QtWidgets.QCheckBox("Move neck")
        self.neck_checkbox.setChecked(True)

        self.freeze_checkbox = QtWidgets.QCheckBox("Freeze transforms")
        self.freeze_checkbox.setChecked(True)

        self.transfer_btn = QtWidgets.QPushButton("transfer")
        self.transfer_btn.setFixedHeight(30)
        self.transfer_btn.clicked.connect(self.transfer)

        joints_lyt.addWidget(self.head)
        joints_lyt.addWidget(self.teeth)
        joints_lyt.addWidget(self.left_eye)
        joints_lyt.addWidget(self.right_eye)
        joints_lyt.addWidget(self.neck_checkbox)
        joints_lyt.addWidget(self.freeze_checkbox)
        joints_lyt.addWidget(self.transfer_btn)
        joints_lyt.addStretch()

        # update dna
        self.update_dna_widget = QtWidgets.QWidget()

        update_dna_lyt = QtWidgets.QVBoxLayout()
        self.update_dna_widget.setLayout(update_dna_lyt)

        self.dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "dna file")

        self.scale_spin = mhWidgets.LabelledDoubleSpinBox(
            "scale", label_width=80, spin_box_width=80, height=30, default=1.0
        )

        self.scale_spin.spin_box.setDecimals(4)
        self.scale_spin.spin_box.setMinimum(0.0)
        self.scale_spin.spin_box.setMaximum(100000.0)

        self.update_mesh_checkbox = QtWidgets.QCheckBox("update meshes")
        self.update_mesh_checkbox.setChecked(True)

        self.update_joint_xforms_checkbox = QtWidgets.QCheckBox("update joint xforms")
        self.update_joint_xforms_checkbox.setChecked(True)

        self.update_joint_list_checkbox = QtWidgets.QCheckBox("update joint list")
        self.update_joint_list_checkbox.setChecked(True)

        self.calculate_lods_checkbox = QtWidgets.QCheckBox("calculate lods")
        self.calculate_lods_checkbox.setChecked(True)

        self.json_checkbox = QtWidgets.QCheckBox("json")

        self.update_btn = QtWidgets.QPushButton("Update")
        self.update_btn.clicked.connect(self.update_dna)

        update_dna_lyt.addWidget(self.dna_file_combo)
        update_dna_lyt.addWidget(self.scale_spin)
        update_dna_lyt.addWidget(self.update_mesh_checkbox)
        update_dna_lyt.addWidget(self.update_joint_xforms_checkbox)
        update_dna_lyt.addWidget(self.update_joint_list_checkbox)
        update_dna_lyt.addWidget(self.calculate_lods_checkbox)
        update_dna_lyt.addWidget(self.json_checkbox)
        update_dna_lyt.addWidget(self.update_btn)
        update_dna_lyt.addStretch()

        # main lyt
        self.tabs.addTab(self.transfer_meshes_widget, "1. Meshes")
        self.tabs.addTab(self.transfer_joints_widget, "2. Joints")
        self.tabs.addTab(self.update_dna_widget, "3. Update DNA")

        # lyt.addWidget(self.transfer_meshes_widget)
        # lyt.addWidget(self.mesh_utils_group_box)
        # lyt.addWidget(self.transfer_joints_widget)
        # lyt.addWidget(self.update_dna_widget)
        # lyt.addStretch()

    def refresh(self):
        self.dna_file_combo.refresh()

    def transfer(self):

        root_joint = "neck_01"

        orig_neck_pos = cmds.xform("neck_01", query=True, translation=True, worldSpace=True)

        cmds.undoInfo(openChunk=True)

        try:
            if self.head.checkbox.isChecked():
                mhFaceJoints.transfer_joint_placement(
                    root_joint, self.head.src.node, self.head.dst.node
                )

            if self.teeth.checkbox.isChecked():
                mhFaceJoints.transfer_teeth(
                    self.teeth.src.node, self.teeth.dst.node
                )

            if self.left_eye.checkbox.isChecked():
                mhFaceJoints.transfer_eye(
                    self.left_eye.src.node, self.left_eye.dst.node, "L"
                )

            if self.right_eye.checkbox.isChecked():
                mhFaceJoints.transfer_eye(
                    self.right_eye.src.node, self.right_eye.dst.node, "R"
                )

            if self.neck_checkbox.isChecked():
                mhFaceJoints.restore_neck_spine_offset(orig_neck_pos)

            if self.freeze_checkbox.isChecked():
                cmds.cutKey("FACIAL_C_FacialRoot")
                cmds.makeIdentity(root_joint, apply=True, r=True)

            cmds.undoInfo(closeChunk=True)

        except Exception as err:
            cmds.undoInfo(closeChunk=True)
            raise err

        return True

    def update_dna(self):

        # check that at least one box is checked
        scale_value = float(self.scale_spin.spin_box.value())

        if not any([
            scale_value != 1.0,
            self.update_mesh_checkbox.isChecked(),
            self.update_joint_xforms_checkbox.isChecked(),
            self.update_joint_list_checkbox.isChecked(),
            self.calculate_lods_checkbox.isChecked(),
            self.json_checkbox.isChecked(),
        ]):
            self.error("No update options checked")
            return False

        # get path
        input_dna_path = self.dna_file_combo.get_path()

        # check we have an input path
        if not input_dna_path:
            self.error("No input DNA path given")
            return False

        # check we have an output path
        if not self.project.output_dna_path:
            self.error("No output DNA path given")
            return False

        # confirm with user
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "This will update input dna file:\n\n{}\n\nThen write output dna file to: \n\n{}\n\nContinue?".format(
                input_dna_path, self.project.output_dna_path
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return False

        dna_obj = DNAReader.read(input_dna_path, Layer.all)

        calib_reader = dnacalib2.DNACalibDNAReader(dna_obj._reader)

        if scale_value != 1.0:
            mhUtils.scale_dna(calib_reader, scale_value)

        if self.update_joint_xforms_checkbox.isChecked():
            mhJoints.update_joint_neutral_xforms(calib_reader, err=False)

        if self.update_joint_list_checkbox.isChecked():
            mhJoints.update_joint_list(calib_reader, verbose=True)

        if self.update_mesh_checkbox.isChecked():
            mhMesh.update_meshes_from_scene(dna_obj, calib_reader)

        if self.calculate_lods_checkbox.isChecked():
            mhMesh.calculate_lods(dna_obj, calib_reader)

        mhUtils.save_dna(
            calib_reader,
            self.project.output_dna_path,
            validate=False,
            as_json=self.json_checkbox.isChecked()
        )

        status = dna.Status.get().message

        if not dna.Status.isOk():
            self.error(QtWidgets.QMessageBox.Ok)
            return False

        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "Dna file exported:\n{}".format(self.project.output_dna_path),
            QtWidgets.QMessageBox.Ok
        )

        return True

    def transfer_face_meshes(self):
        try:
            mhFaceMeshes.transfer_face_meshes(
                transfer_eyeballs=self.eyeballs_checkbox.isChecked(),
                transfer_eyelashes=self.eyelashes_checkbox.isChecked(),
                transfer_eyewet=self.eyewet_checkbox.isChecked(),
                transfer_inner_mouth=self.inner_mouth_checkbox.isChecked(),
                # recalculate_pivots=self.eye_pivots_checkbox.isChecked(),
                cleanup=self.cleanup_checkbox.isChecked(),
            )
        except mhCore.MHError as err:
            self.error(err)

    def prefix_meshes(self):
        cmds.undoInfo(openChunk=True)

        try:
            for mesh in cmds.listRelatives("head_lod0_grp", fullPath=True):
                mesh_name = mesh.split("|")[-1]

                cmds.rename(
                    mesh, "src_{}".format(mesh_name)
                )

            cmds.undoInfo(closeChunk=True)

        except Exception as err:
            cmds.undoInfo(closeChunk=True)
            self.error(err)

        return True

    def _eyewet_post_clicked(self):
        mhFaceMeshes.eyewet_post()

    def _create_eyelid_wrap_meshes_clicked(self):
        mhFaceMeshes.create_eyelid_wrapper_meshes(
            "head_lod0_mesh",
            "eyeLeft_lod0_mesh",
            "eyeRight_lod0_mesh",
        )


class DnaInspectWidget(QtWidgets.QMainWindow):
    """
    inspect PSDs
    row = input expression
    column = output combos
    maybe???

    """

    def __init__(self, dna_path, lod, *args, **kwargs):
        super(DnaInspectWidget, self).__init__(*args, **kwargs)

        filename = os.path.basename(dna_path)

        self.setWindowTitle(filename)

        dna_obj = DNAReader.read(dna_path, Layer.all)
        calib_reader = dnacalib2.DNACalibDNAReader(dna_obj._reader)

        # mesh text
        mesh_fmt = "    {mesh_name}: {point_count} points, {blendshape_count} blendshape targets\n"

        mesh_txt = ""

        mesh_indices = mhMesh.get_mesh_indices(dna_obj, calib_reader, lod=lod)
        meshes = dna_obj.get_meshes()

        for mesh_index in mesh_indices:
            mesh_txt += mesh_fmt.format(
                mesh_name=meshes[mesh_index].name,
                point_count=calib_reader.getVertexPositionCount(mesh_index),
                blendshape_count=calib_reader.getBlendShapeTargetCount(mesh_index)
            )

        mesh_txt = "Meshes:\n\n{}".format(mesh_txt)

        # summary
        summary_text = """
Summary:

Path: {path}
Joint count: {joint_count}
Mesh count: {mesh_count}
        """.format(
            path=dna_path,
            joint_count=calib_reader.getJointCount(),
            mesh_count=calib_reader.getMeshCount(),
        )

        # blendshape text
        blendshape_channel_names = [
            calib_reader.getBlendShapeChannelName(i)
            for i in range(calib_reader.getBlendShapeChannelCount())
        ]

        blendshape_channel_text = [
            "{}: {}".format(i, name) for i, name in enumerate(blendshape_channel_names)
        ]

        blendshape_channel_text = "\n".join(blendshape_channel_text)
        blendshape_channel_text = "blendshape Channels:\n\n{}".format(blendshape_channel_text)

        # raw controls text
        raw_controls_names = [
            "{}: {}".format(i, calib_reader.getRawControlName(i))
            for i in range(calib_reader.getRawControlCount())
        ]

        raw_controls_text = "\n".join(raw_controls_names)
        raw_controls_text = "Raw Controls:\n\n{}".format(raw_controls_text)

        # joint column to blendshape channels
        columns_to_blendshapes = mhBehaviour.get_columns_to_blendshape_channels(calib_reader)

        columns_to_blendshapes_text = ["{}: {}".format(i, name) for i, name in enumerate(columns_to_blendshapes)]
        columns_to_blendshapes_text = "\n".join(columns_to_blendshapes_text)
        columns_to_blendshapes_text = "Joint columns to blendshape channels:\n\n{}".format(columns_to_blendshapes_text)

        # gui
        gui_control_names = [
            "{}: {}".format(i, calib_reader.getGUIControlName(i))
            for i in range(calib_reader.getGUIControlCount())
        ]

        gui_controls_text = "\n".join(gui_control_names)
        gui_controls_text = "GUI Controls:\n\n{}".format(gui_controls_text)

        # psd
        psd_inputs = calib_reader.getPSDColumnIndices()
        psd_outputs = calib_reader.getPSDRowIndices()

        psd_mapping = {}

        for psd_input, psd_output in zip(psd_inputs, psd_outputs):
            if psd_output in psd_mapping:
                psd_mapping[psd_output].append(psd_input)
            else:
                psd_mapping[psd_output] = [psd_input]

        psd_text = "PSDs:\n"

        for psd_output in sorted(psd_mapping.keys()):
            psd_name = columns_to_blendshapes[psd_output]

            if psd_name is None:
                psd_name = str(psd_output)

            psd_text += "{}: ".format(psd_name)

            for i in psd_mapping[psd_output]:
                input_name = None

                if i < len(columns_to_blendshapes):
                    input_name = columns_to_blendshapes[i]

                if input_name is None:
                    input_name = str(i)

                psd_text += "{}, ".format(input_name)

            psd_text += "\n"

        # print to output
        print(summary_text)
        print(mesh_txt)

        # widgets
        self.summary_label = QtWidgets.QLabel(summary_text)
        self.summary_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.meshes_label = QtWidgets.QLabel(mesh_txt)
        self.meshes_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.meshes_scroll_area = QtWidgets.QScrollArea()
        self.meshes_scroll_area.setWidget(self.meshes_label)

        self.raw_controls_label = QtWidgets.QLabel(raw_controls_text)
        self.raw_controls_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.raw_controls_scroll_area = QtWidgets.QScrollArea()
        self.raw_controls_scroll_area.setWidget(self.raw_controls_label)

        self.gui_controls_label = QtWidgets.QLabel(gui_controls_text)
        self.gui_controls_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.gui_controls_scroll_area = QtWidgets.QScrollArea()
        self.gui_controls_scroll_area.setWidget(self.gui_controls_label)

        self.blendshape_channel_label = QtWidgets.QLabel(blendshape_channel_text)
        self.blendshape_channel_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.blendshape_channel_scroll_area = QtWidgets.QScrollArea()
        self.blendshape_channel_scroll_area.setWidget(self.blendshape_channel_label)

        self.columns_to_blendshapes_label = QtWidgets.QLabel(columns_to_blendshapes_text)
        self.columns_to_blendshapes_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.columns_to_blendshapes_scroll_area = QtWidgets.QScrollArea()
        self.columns_to_blendshapes_scroll_area.setWidget(self.columns_to_blendshapes_label)

        self.psds_label = QtWidgets.QLabel(psd_text)
        self.psds_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.psds_scroll_area = QtWidgets.QScrollArea()
        self.psds_scroll_area.setWidget(self.psds_label)

        self.setCentralWidget(QtWidgets.QWidget())

        self.lyt = QtWidgets.QVBoxLayout()

        self.lyt.addWidget(self.summary_label)
        self.lyt.addWidget(self.meshes_scroll_area)
        self.lyt.addWidget(self.raw_controls_scroll_area)
        self.lyt.addWidget(self.gui_controls_scroll_area)
        self.lyt.addWidget(self.blendshape_channel_scroll_area)
        self.lyt.addWidget(self.columns_to_blendshapes_scroll_area)
        self.lyt.addWidget(self.psds_scroll_area)

        self.centralWidget().setLayout(self.lyt)


class DnaBuildWidget(mhWidgets.Tab):
    class DnaMenu(QtWidgets.QMenu):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.setTitle("dna")

            empty_icon = QtGui.QIcon()

            self.inspect_action = QtWidgets.QAction(empty_icon, 'inspect dna', self)
            self.inspect_action.setStatusTip('view data contained within dna file')
            self.addAction(self.inspect_action)

    class RigMenu(QtWidgets.QMenu):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.setTitle("rig")

            empty_icon = QtGui.QIcon()

            self.joint_look_action = QtWidgets.QAction(empty_icon, 'set joint look', self)
            self.joint_look_action.setStatusTip('make joints easier to see')
            self.addAction(self.joint_look_action)

            self.add_spine_joints_action = QtWidgets.QAction(empty_icon, 'add spine joints', self)
            self.add_spine_joints_action.setStatusTip('add full spine hierarchy for Unreal')
            self.addAction(self.add_spine_joints_action)

            self.add_exp_attrs_action = QtWidgets.QAction(empty_icon, 'add expression attrs', self)
            self.add_exp_attrs_action.setStatusTip('Add attributes required for Unreal')
            self.addAction(self.add_exp_attrs_action)

    class MaterialsMenu(QtWidgets.QMenu):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.setTitle("materials")

            empty_icon = QtGui.QIcon()

            self.import_materials_action = QtWidgets.QAction(empty_icon, 'import materials', self)
            self.import_materials_action.setStatusTip('Import metahuman base materials')
            self.addAction(self.import_materials_action)

            self.repath_common_action = QtWidgets.QAction(empty_icon, 'repath common textures', self)
            self.repath_common_action.setStatusTip('Repath common textures')
            self.addAction(self.repath_common_action)

            self.repath_asset_action = QtWidgets.QAction(empty_icon, 'repath asset textures', self)
            self.repath_asset_action.setStatusTip('Add attributes required for Unreal')
            self.addAction(self.repath_asset_action)

            self.reset_materials_action = QtWidgets.QAction(empty_icon, 'reset materials', self)
            self.reset_materials_action.setStatusTip('reset all materials back to default lambert')
            self.addAction(self.reset_materials_action)

            self.create_lamberts_action = QtWidgets.QAction(empty_icon, 'create lamberts', self)
            self.create_lamberts_action.setStatusTip('Create basic lambert per mesh')
            self.addAction(self.create_lamberts_action)

            self.create_lights_action = QtWidgets.QAction(empty_icon, 'create lights', self)
            self.create_lights_action.setStatusTip('Create lights to work well with metahuman textures')
            self.addAction(self.create_lights_action)

    def __init__(self, project, parent=None):
        super(DnaBuildWidget, self).__init__(project, parent=parent)

        self._create_widgets()
        self._create_menus()

    def _create_menus(self):
        self.menubar = self.menuBar()

        # dna utils
        self.dna_menu = self.DnaMenu(parent=self)
        self.menubar.addMenu(self.dna_menu)

        self.dna_menu.inspect_action.triggered.connect(self.inspect_dna)

        # build utils
        self.rig_menu = self.RigMenu(parent=self)
        self.menubar.addMenu(self.rig_menu)

        self.rig_menu.joint_look_action.triggered.connect(self.set_look)
        self.rig_menu.add_spine_joints_action.triggered.connect(self.add_spine)
        self.rig_menu.add_exp_attrs_action.triggered.connect(self.add_exp)

        # material utils
        self.materials_menu = self.MaterialsMenu(parent=self)
        self.menubar.addMenu(self.materials_menu)

        self.materials_menu.import_materials_action.triggered.connect(self.import_materials)
        self.materials_menu.repath_common_action.triggered.connect(self.repath_common)
        self.materials_menu.repath_asset_action.triggered.connect(self.repath_asset)
        self.materials_menu.reset_materials_action.triggered.connect(self.reset_materials)
        self.materials_menu.create_lamberts_action.triggered.connect(self.create_lamberts)
        self.materials_menu.create_lights_action.triggered.connect(self.create_lights)

    def _create_widgets(self):
        lyt = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(lyt)

        # build
        self.build_group_box = QtWidgets.QGroupBox("build rig")

        build_lyt = QtWidgets.QVBoxLayout()
        self.build_group_box.setLayout(build_lyt)

        self.dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "dna file")

        self.gui_override_widget = mhWidgets.PathOpenWidget("gui override")

        self.partial_rig_group_box = QtWidgets.QGroupBox("Partial Rig")
        self.partial_rig_group_box.setCheckable(True)
        self.partial_rig_group_box.setChecked(False)

        self.joints_checkbox = QtWidgets.QCheckBox("joints")
        self.skin_cluster_checkbox = QtWidgets.QCheckBox("skin cluster")
        self.blendshapes_checkbox = QtWidgets.QCheckBox("blendshapes")

        self.partial_rig_lyt = QtWidgets.QVBoxLayout()

        self.partial_rig_lyt.addWidget(self.joints_checkbox)
        self.partial_rig_lyt.addWidget(self.skin_cluster_checkbox)
        self.partial_rig_lyt.addWidget(self.blendshapes_checkbox)

        self.partial_rig_group_box.setLayout(self.partial_rig_lyt)

        self.build_btn = QtWidgets.QPushButton("Build")
        self.build_btn.setFixedHeight(30)
        self.build_btn.clicked.connect(self.build_rig)

        build_lyt.addWidget(self.dna_file_combo)
        build_lyt.addWidget(self.gui_override_widget)
        build_lyt.addWidget(self.partial_rig_group_box)
        build_lyt.addWidget(self.build_btn)

        # TODO
        # self.repath_widget = mhWidgets.RepathWidget()

        # main lyt
        lyt.addWidget(self.build_group_box)
        lyt.addStretch()

    def refresh(self):
        self.dna_file_combo.refresh()

    def set_look(self):
        cmds.undoInfo(openChunk=True)

        try:
            mhFaceJoints.set_joint_look()
            cmds.undoInfo(closeChunk=True)
        except Exception as err:
            cmds.undoInfo(closeChunk=True)
            raise err

    def add_spine(self):
        cmds.undoInfo(openChunk=True)

        try:
            mhUeUtils.add_root_and_spine()
            cmds.undoInfo(closeChunk=True)

        except Exception as err:
            cmds.undoInfo(closeChunk=True)
            raise err

    def add_exp(self):
        cmds.undoInfo(openChunk=True)

        try:
            mhUeUtils.add_ctrl_exp_pose_attrs()
            mhUeUtils.key_pose_attrs()
            cmds.undoInfo(closeChunk=True)

        except Exception as err:
            cmds.undoInfo(closeChunk=True)
            raise err

    def create_lamberts(self):
        mhMayaUtils.create_materials_for_hierarchy(
            "head_lod0_grp", "lambert", suffix="_material"
        )

    def import_materials(self):

        try:
            file_path = os.path.join(mhCore.DATA_DIR, "materials.ma")

            print("Importing file: {}".format(file_path))
            cmds.file(file_path, i=True)

            mhFaceMaterials.apply_materials(lod=0)

            if cmds.objExists("FRM_WMmultipliers"):
                mhFaceMaterials.connect_channels()

        except Exception as err:
            self.error(err)

        return True

    def export_asset_materials(self):
        try:
            file_path = mhFaceMaterials.export_asset_materials()

            QtWidgets.QMessageBox.information(
                self,
                "Info",
                "materials exported: {}".format(file_path),
                QtWidgets.QMessageBox.Ok
            )

        except Exception as err:
            self.error(err)

        return True

    def apply_asset_materials(self):
        try:
            mhFaceMaterials.apply_materials(lod=0)
        except Exception as err:
            self.error(err)

    def reset_materials(self):
        mhFaceMaterials.reset_materials()

    def _repath_dialog(self, name):

        paths = mhFaceMaterials.find_paths(name)

        if not paths:
            self.error("No paths found: {}".format(name))
            return False

        new_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Repath: {}".format(name),
            paths[0],
        )

        if not new_path:
            print("Cancelled")
            return False

        attrs = cmds.filePathEditor(query=True, listFiles="", attributeOnly=True)

        for path in paths:
            print("Repathing: {} -> {}".format(path, new_path))

            cmds.filePathEditor(
                attrs,
                replaceString=[path, new_path],
                replaceAll=True
            )

        return True

    def repath_common(self):
        self._repath_dialog("Common")

    def repath_asset(self):
        paths = mhFaceMaterials.find_asset_paths()

        if not paths:
            self.error("No assets found")
            return

        asset = os.path.split(paths[0])[1]
        self._repath_dialog(asset)

    def create_lights(self):
        light_1 = cmds.directionalLight()
        light_2 = cmds.directionalLight()
        light_3 = cmds.directionalLight()

        light_1_transform = cmds.listRelatives(light_1, parent=True)[0]
        light_2_transform = cmds.listRelatives(light_2, parent=True)[0]
        light_3_transform = cmds.listRelatives(light_3, parent=True)[0]

        cmds.xform(light_1_transform, translation=(15, 150, 0), rotation=(-20, 30, 0))
        cmds.xform(light_2_transform, translation=(15, 150, 0), rotation=(0, 120, 0))
        cmds.xform(light_3_transform, translation=(15, 150, 0), rotation=(0, -120, 0))

        return True

    def inspect_dna(self, lod=0):
        dna_path = self.dna_file_combo.get_path()

        if not os.path.exists(dna_path):
            self.error("Dna path not found: {}".format(dna_path))
            return False

        self.inspect_widget = DnaInspectWidget(dna_path, lod, parent=self)
        self.inspect_widget.show()

        return True

    def build_rig(self):
        try:
            mhSrc.validate_plugin()
        except mhCore.MHError as err:
            self.error(err)
            return False

        dna_path = self.dna_file_combo.get_path()

        if not os.path.exists(dna_path):
            self.error("Dna path not found: {}".format(dna_path))
            return False

        # confirm
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "Build rig?\n{}".format(dna_path),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return None

        if self.partial_rig_group_box.isChecked():
            mhUtils.import_components(
                dna_path,
                self.project.dna_assets_path,
                add_joints=self.joints_checkbox.isChecked(),
                add_rig_logic=False,
                add_skin_cluster=self.skin_cluster_checkbox.isChecked(),
                add_blend_shapes=self.blendshapes_checkbox.isChecked(),
                lod=0,
                scene_up="y",
            )
        else:
            mhUtils.import_components(
                dna_path,
                self.project.dna_assets_path,
                add_joints=True,
                add_rig_logic=True,
                add_skin_cluster=True,
                add_blend_shapes=True,
                lod=None,
                scene_up="y",
                gui_ctrls_path=self.gui_override_widget.path
            )

        return True


class PosesTab(mhWidgets.Tab):
    class UtilsMenu(QtWidgets.QMenu):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.setTitle("utils")

            empty_icon = QtGui.QIcon()

            self.import_action = QtWidgets.QAction(empty_icon, 'import dna', self)
            self.import_action.setStatusTip('import poses')
            self.import_action.triggered.connect(self._import)
            self.addAction(self.import_action)

            self.export_action = QtWidgets.QAction(empty_icon, 'export dna', self)
            self.export_action.setStatusTip('export dna')
            self.export_action.triggered.connect(self._export)
            self.addAction(self.export_action)

            self.addSeparator()

            self.scale_all_action = QtWidgets.QAction(empty_icon, 'scale all deltas', self)
            self.scale_all_action.setStatusTip('scale translation deltas for all poses')
            self.addAction(self.scale_all_action)

            self.init_bs_action = QtWidgets.QAction(empty_icon, 'init pose blendshapes', self)
            self.init_bs_action.setStatusTip('Initialize blendshapes for all poses')
            self.addAction(self.init_bs_action)

            self.find_opposites_action = QtWidgets.QAction(empty_icon, 'find opposites', self)
            self.find_opposites_action.setStatusTip('Find opposite pose for all poses')
            self.addAction(self.find_opposites_action)

            self.refresh_action = QtWidgets.QAction(empty_icon, 'refresh', self)
            self.refresh_action.setStatusTip('refresh data')
            self.refresh_action.triggered.connect(self._refresh)
            self.addAction(self.refresh_action)

            self.reset_action = QtWidgets.QAction(empty_icon, 'reset', self)
            self.reset_action.setStatusTip('reset data')
            self.reset_action.triggered.connect(self._reset)
            self.addAction(self.reset_action)

        def _import(self):
            dialog = PosesTab.ImportDialog(
                self.parent().project, parent=self.parent()
            )

            dialog.open()

        def _export(self):
            # check we have data loaded
            if not self.parent().project.pose_manager:
                QtWidgets.QMessageBox.critical(
                    self.parent(),
                    "Error",
                    "No pose data to export",
                    QtWidgets.QMessageBox.Ok
                )

                return

            dialog = PosesTab.ExportDialog(
                self.parent().project, parent=self.parent()
            )

            dialog.open()

        def _refresh(self):
            self.parent().refresh()

        def _reset(self):
            confirm = QtWidgets.QMessageBox.warning(
                self.parent(),
                "confirm",
                "Reset all pose manager data?",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
            )

            if confirm is QtWidgets.QMessageBox.Cancel:
                return

            self.parent().project.pose_manager.reset()
            self.parent().refresh()

    class ImportDialog(mhWidgets.Dialog):
        def __init__(self, project, parent=None):
            super().__init__(project, parent=parent)

            self.setWindowTitle("Import dna")

            self.create_widgets()

            self.resize(600, 100)

        def create_widgets(self):
            self.dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "dna file")
            self.dna_file_combo.refresh()

            self.bake_config_checkbox = QtWidgets.QCheckBox("include bake config")

            lyt = QtWidgets.QVBoxLayout()
            lyt.addWidget(self.dna_file_combo)
            lyt.addWidget(self.bake_config_checkbox)
            self.setLayout(lyt)

            self.add_accept_reject_buttons(accept="load")

        def do_action(self):
            dna_path = self.dna_file_combo.get_path()

            # check we have paths
            if not dna_path:
                self.error("No DNA path given")
                return False

            use_bake_config = self.bake_config_checkbox.isChecked()

            if use_bake_config:
                if not self.project.bake_config_path:
                    self.error("No bake config path given")

            # load dna and get poses
            mhBehaviour.load_poses_from_dna(dna_path, pose_manager=self.project.pose_manager)

            if use_bake_config:
                bake_config = mhBakeRig.BakeConfig.load(self.project.bake_config_path)

                bake_config.update_pose_manager(self.project.pose_manager)

            self.parent().refresh()

            return True

    class ExportDialog(mhWidgets.Dialog):
        def __init__(self, project, parent=None):
            super().__init__(project, parent=parent)

            self.setWindowTitle("Export dna")

            self.create_widgets()

            self.resize(600, 100)

        def create_widgets(self):
            self.input_dna_combo = mhWidgets.DnaPathManagerWidget(self.project, "input dna file")
            self.input_dna_combo.combo.setCurrentIndex(0)
            self.input_dna_combo.refresh()

            self.output_dna_combo = mhWidgets.DnaPathManagerWidget(self.project, "output dna file")
            self.output_dna_combo.combo.setCurrentIndex(1)
            self.output_dna_combo.refresh()

            lyt = QtWidgets.QVBoxLayout()
            lyt.addWidget(self.input_dna_combo)
            lyt.addWidget(self.output_dna_combo)

            self.setLayout(lyt)

            self.add_accept_reject_buttons(accept="Export")

        def do_action(self):
            # TODO support writing new poses to dna
            input_dna_path = self.input_dna_combo.get_path()
            output_dna_path = self.output_dna_combo.get_path()

            # check we have an output path
            if not input_dna_path:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    "No input DNA path given",
                    QtWidgets.QMessageBox.Ok
                )

                return False

            if not output_dna_path:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    "No output DNA path given",
                    QtWidgets.QMessageBox.Ok
                )

                return False

            # confirm
            confirm = QtWidgets.QMessageBox.warning(
                self,
                "confirm",
                "Save all poses?\ninput: {}\noutput: {}".format(input_dna_path, output_dna_path),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
            )

            if confirm is QtWidgets.QMessageBox.Cancel:
                return False

            # read dna file to update
            reader = mhUtils.load_dna(input_dna_path)
            calib_reader = dnacalib2.DNACalibDNAReader(reader)

            # write data
            mhBehaviour.save_dna(
                calib_reader,
                output_dna_path,
                poses=self.project.pose_manager.poses,
            )

            # confirm write
            if not dna.Status.isOk():
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    status,
                    QtWidgets.QMessageBox.Ok
                )
                return False
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Success",
                    "Dna file exported:\n{}".format(output_dna_path),
                    QtWidgets.QMessageBox.Ok
                )
                return True

    def __init__(self, project, parent=None):
        super(PosesTab, self).__init__(project, parent=parent)

        self._create_menus()
        self._create_widgets()

    def _create_menus(self):
        self.menubar = self.menuBar()

        # dna utils
        self.utils_menu = self.UtilsMenu(parent=self)
        self.menubar.addMenu(self.utils_menu)

        self.utils_menu.scale_all_action.triggered.connect(self.scale_all_poses)
        self.utils_menu.init_bs_action.triggered.connect(self.init_blendshapes)
        self.utils_menu.find_opposites_action.triggered.connect(self.find_opposites)

    def _create_widgets(self):
        # pose model
        self.pose_model = mhPoseWidgets.PosesModel()
        self.pose_model.set_pose_manager(self.project.pose_manager)

        # tabs
        self.tabs = QtWidgets.QTabWidget()

        # mesh blendshapes
        self.mesh_blendshapes_widget = mhPoseWidgets.MeshBlendshapesWidget(
            self.project
        )

        self.tabs.addTab(self.mesh_blendshapes_widget, "meshes")

        # configure poses
        self.configure_widget = QtWidgets.QWidget()
        self.configure_lyt = QtWidgets.QVBoxLayout()

        self.configure_widget.setLayout(self.configure_lyt)

        self.pose_widget = mhPoseWidgets.PoseWidget(
            self.project.pose_config_view_settings
        )

        self.pose_widget.add_pose_mode_combo()
        self.pose_widget.set_pose_model(self.pose_model)

        self.configure_lyt.addWidget(self.pose_widget)

        self.tabs.addTab(self.configure_widget, "configure")

        # edit
        self.splitter = QtWidgets.QSplitter()

        self.core_poses_widget = mhPoseWidgets.PoseEditorWidget(
            self.project.core_pose_view_settings,
            pose_mode=mhPoseWidgets.PoseMode.CorePoses
        )

        self.combo_poses_widget = mhPoseWidgets.PoseEditorWidget(
            self.project.combo_pose_view_settings,
            pose_mode=mhPoseWidgets.PoseMode.ComboPoses
        )

        self.core_poses_widget.set_pose_model(self.pose_model)
        self.combo_poses_widget.set_pose_model(self.pose_model)

        self.splitter.addWidget(self.core_poses_widget)
        self.splitter.addWidget(self.combo_poses_widget)

        self.tabs.addTab(self.splitter, "edit")

        # main layout
        self.setCentralWidget(self.tabs)

        self.core_poses_widget.pose_widget.SELECTION_CHANGED.connect(self.core_selection_changed)
        self.combo_poses_widget.pose_widget.SELECTION_CHANGED.connect(self.combo_selection_changed)

    def core_selection_changed(self, *args):
        poses = self.core_poses_widget.get_selected_poses(warn=False)
        self.combo_poses_widget.set_ref_poses(poses)

    def combo_selection_changed(self, *args):
        poses = self.combo_poses_widget.get_selected_poses(warn=False)
        self.core_poses_widget.set_ref_poses(poses)

    def refresh(self):
        self.mesh_blendshapes_widget.refresh()
        self.pose_model.refresh()
        self.core_poses_widget.refresh()
        self.combo_poses_widget.refresh()
        self.pose_widget.refresh()
        return True

    def init_blendshapes(self):
        if not self.project.pose_manager:
            self.error("Poses not loaded")
            return

        self.project.pose_manager.initialize_shape_names()

        self.refresh()

        QtWidgets.QMessageBox.information(
            self,
            "Complete",
            "Shape names initialized",
            QtWidgets.QMessageBox.Ok
        )

    def scale_all_poses(self):
        scale_value, ok = QtWidgets.QInputDialog.getDouble(
            self, "Scale poses", "Value to scale translate values of all poses:",
            value=1.0, min=0.0, max=10000, decimals=3
        )

        if not ok:
            return False

        scale_value = float(scale_value)

        for pose in self.poses:
            pose.scale_deltas(scale_value)

        return True

    def find_opposites(self):
        # TODO dialog or settings
        self.project.pose_manager.find_opposites("L", "R", ends_with=True)
        self.refresh()


class ConnectControlBoardsDialog(mhWidgets.Dialog):
    def __init__(self, project, parent=None):
        super().__init__(project, parent=parent)

        self.setWindowTitle("Connect control boards")

        self.resize(500, 100)

        self.create_widgets()

    def create_widgets(self):
        self.src_namespace_edit = mhWidgets.LabelledNamespaceLineEdit("Src Namespace")
        self.src_namespace_edit.set_from_selected()

        self.dst_namespace_edit = mhWidgets.LabelledNamespaceLineEdit("Dst Namespace")
        self.dst_namespace_edit.set_from_selected(index=1)

        lyt = QtWidgets.QVBoxLayout()
        lyt.addWidget(self.src_namespace_edit)
        lyt.addWidget(self.dst_namespace_edit)

        self.setLayout(lyt)
        self.add_accept_reject_buttons(accept="Connect")

    def do_action(self):
        src_namespace = self.src_namespace_edit.line_edit.text()
        dst_namespace = self.dst_namespace_edit.line_edit.text()
        return mhAnimUtils.connect_control_boards(src_namespace, dst_namespace)


class DisconnectControlBoardsDialog(mhWidgets.Dialog):
    def __init__(self, project, parent=None):
        super().__init__(project, parent=parent)

        self.setWindowTitle("Disconnect control boards")

        self.resize(500, 100)

        self.create_widgets()

    def create_widgets(self):
        self.src_namespace_edit = mhWidgets.LabelledNamespaceLineEdit("Src Namespace")
        self.src_namespace_edit.set_from_selected()

        self.dst_namespace_edit = mhWidgets.LabelledNamespaceLineEdit("Dst Namespace")
        self.dst_namespace_edit.set_from_selected(index=1)

        lyt = QtWidgets.QVBoxLayout()
        lyt.addWidget(self.src_namespace_edit)
        lyt.addWidget(self.dst_namespace_edit)

        self.setLayout(lyt)
        self.add_accept_reject_buttons(accept="Disconnect")

    def do_action(self):
        src_namespace = self.src_namespace_edit.line_edit.text()
        dst_namespace = self.dst_namespace_edit.line_edit.text()
        return mhAnimUtils.disconnect_control_boards(src_namespace, dst_namespace)


class TechRomDialog(mhWidgets.Dialog):
    def __init__(self, project, parent=None):
        super().__init__(project, parent=parent)

        self.setWindowTitle("Create tech ROM")

        self.resize(500, 300)

        self.create_widgets()

    def create_widgets(self):
        self.dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "dna file")
        self.dna_file_combo.refresh()

        self.namespace_edit = mhWidgets.LabelledNamespaceLineEdit("Namespace")
        self.namespace_edit.set_from_selected()

        self.start_spin = mhWidgets.LabelledSpinBox("Start Frame", default=0, maximum=10000)
        self.frame_interval = mhWidgets.LabelledSpinBox("Frame Interval", default=10, maximum=100)
        self.update_timeline_checkbox = QtWidgets.QCheckBox("Update Timeline")
        self.combos_checkbox = QtWidgets.QCheckBox("Combos")
        self.use_bake_config_checkbox = QtWidgets.QCheckBox("Use Bake Config")
        self.combine_lr_checkbox = QtWidgets.QCheckBox("Combine LR")
        self.annotate_checkbox = QtWidgets.QCheckBox("Annotate")
        self.selected_sculpts_checkbox = QtWidgets.QCheckBox("Selected Sculpts")

        self.update_timeline_checkbox.setChecked(True)
        self.combos_checkbox.setChecked(True)
        self.use_bake_config_checkbox.setChecked(False)
        self.combine_lr_checkbox.setChecked(True)
        self.annotate_checkbox.setChecked(True)

        lyt = QtWidgets.QVBoxLayout()
        self.setLayout(lyt)

        lyt.addWidget(self.dna_file_combo)
        lyt.addWidget(self.namespace_edit)
        lyt.addWidget(self.start_spin)
        lyt.addWidget(self.frame_interval)
        lyt.addWidget(self.update_timeline_checkbox)
        lyt.addWidget(self.combos_checkbox)
        lyt.addWidget(self.use_bake_config_checkbox)
        lyt.addWidget(self.combine_lr_checkbox)
        lyt.addWidget(self.annotate_checkbox)
        lyt.addWidget(self.selected_sculpts_checkbox)

        self.add_accept_reject_buttons(accept="Create tech ROM")

        # # Create eye ROM
        # # TODO
        # self.eye_rom_box = QtWidgets.QGroupBox("eye technical ROM")
        #
        # self.eye_start_spin = mhWidgets.LabelledSpinBox("Start Frame", default=0, maximum=10000)
        # self.eye_frame_interval = mhWidgets.LabelledSpinBox("Frame Interval", default=10, maximum=100)
        # self.eye_update_timeline_checkbox = QtWidgets.QCheckBox("Update Timeline")
        #
        # self.eye_update_timeline_checkbox.setChecked(True)
        #
        # self.eye_create_btn = QtWidgets.QPushButton("Create eye ROM")
        # self.eye_create_btn.clicked.connect(self._create_rom_clicked)
        #
        # eye_rom_lyt = QtWidgets.QVBoxLayout()
        # self.eye_rom_box.setLayout(eye_rom_lyt)
        #
        # eye_rom_lyt.addWidget(self.eye_create_btn)

    def do_action(self):

        namespace = self.namespace_edit.line_edit.text()
        update_timeline = self.update_timeline_checkbox.isChecked()
        annotate = self.annotate_checkbox.isChecked()
        combine_lr = self.combine_lr_checkbox.isChecked()
        combos = self.combos_checkbox.isChecked()
        selected_sculpts = self.selected_sculpts_checkbox.isChecked()
        start_frame = self.start_spin.spin_box.value()
        interval = self.frame_interval.spin_box.value()
        tongue = False
        eyelashes = False
        use_bake_config = self.use_bake_config_checkbox.isChecked()
        bake_config_file = self.project.bake_config_path

        if selected_sculpts:
            sculpts = cmds.ls(sl=True, type="transform")
        else:
            sculpts = None

        if combos:
            # get combos from dna file and map to controls
            dna_path = self.dna_file_combo.get_path()

            if not dna_path:
                self.error("No Dna path specified")
                return False

            if not os.path.exists(dna_path):
                self.error("Dna path not found: {}".format(dna_path))
                return False

            LOG.info("Loading dna: {}".format(dna_path))

            pose_manager = mhBehaviour.load_poses_from_dna(dna_path)

            if use_bake_config:
                bake_config = mhBakeRig.BakeConfig.load(bake_config_file)

                bake_config.update_pose_manager(pose_manager)

            mapping = mhAnimUtils.map_expressions_to_controls(
                tongue=tongue, eyelashes=eyelashes, namespace=namespace
            )

            combo_mapping = mhAnimUtils.map_psds_to_controls(
                mapping, pose_manager.combo_poses  # .values()
            )

        else:
            combo_mapping = None

        # animate controls
        for node in [
            mhAnimUtils.ANNOTATION_NAME,
            mhAnimUtils.ORIGINAL_ANNOTATION,
            mhAnimUtils.SCULPT_ANNOTATION,
        ]:
            if cmds.objExists(node):
                cmds.delete(node)

        mhAnimUtils.reset_control_board_anim(namespace=namespace)

        if sculpts:
            mhAnimUtils.reset_sculpts_anim(sculpts)

        mhAnimUtils.animate_ctrl_rom(
            combos=combos,
            combine_lr=combine_lr,
            namespace=namespace,
            start_frame=start_frame,
            interval=interval,
            update_timeline=update_timeline,
            annotate=annotate,
            tongue=tongue,
            eyelashes=eyelashes,
            combo_mapping=combo_mapping,
            sculpts=sculpts,
        )

        return True


class DnaMergeDialog(mhWidgets.Dialog):
    def __init__(self, project, parent=None):
        super().__init__(project, parent=parent)

        self.setWindowTitle("Merge DNA files")

        self.create_widgets()

        self.resize(600, 300)

    def create_widgets(self):
        lyt = QtWidgets.QVBoxLayout()
        self.setLayout(lyt)

        self.src_dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "src dna file")
        self.src_dna_file_combo.refresh()

        self.dst_dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "dst dna file")
        self.dst_dna_file_combo.combo.setCurrentIndex(2)
        self.dst_dna_file_combo.refresh()

        self.output_dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "output dna file")
        self.output_dna_file_combo.combo.setCurrentIndex(1)
        self.output_dna_file_combo.refresh()

        self.joint_xforms_checkbox = QtWidgets.QCheckBox("joint xforms")
        self.vertex_positions_checkbox = QtWidgets.QCheckBox("vertex positions")
        self.poses_checkbox = QtWidgets.QCheckBox("poses")
        self.calculate_lods_checkbox = QtWidgets.QCheckBox("calculate lods")
        self.json_checkbox = QtWidgets.QCheckBox("json")

        lyt.addWidget(self.src_dna_file_combo)
        lyt.addWidget(self.dst_dna_file_combo)
        lyt.addWidget(self.output_dna_file_combo)

        for checkbox in [
            self.joint_xforms_checkbox,
            self.vertex_positions_checkbox,
            self.poses_checkbox,
            self.calculate_lods_checkbox,
        ]:
            checkbox.setChecked(True)
            lyt.addWidget(checkbox)

        lyt.addWidget(self.json_checkbox)

        self.btn_lyt = QtWidgets.QHBoxLayout()

        self.merge_btn = QtWidgets.QPushButton("Merge")
        self.merge_btn.clicked.connect(self._merge_clicked)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        self.btn_lyt.addWidget(self.merge_btn)
        self.btn_lyt.addWidget(self.cancel_btn)

        lyt.addLayout(self.btn_lyt)

        # lyt.addStretch()

    def _merge_clicked(self):

        # check that at least one box is checked
        if not any([
            self.joint_xforms_checkbox.isChecked(),
        ]):
            self.error("No update options checked")
            return False

        # get path
        src_dna_path = self.src_dna_file_combo.get_path()
        dst_dna_path = self.dst_dna_file_combo.get_path()
        output_dna_path = self.output_dna_file_combo.get_path()

        # check we have paths
        if not src_dna_path:
            self.error("No source DNA path given")
            return False

        if not dst_dna_path:
            self.error("No destination DNA path given")
            return False

        if not output_dna_path:
            self.error("No output DNA path given")
            return False

        # confirm with user
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "This will merge source dna file:\n\n{}\n\nInto destination dna file: \n\n{}\n\nThen save output dna file to:\n\n{}\n\nContinue?".format(
                src_dna_path, dst_dna_path, output_dna_path
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return False

        src_dna_obj = DNAReader.read(src_dna_path, Layer.all)
        src_calib_reader = dnacalib2.DNACalibDNAReader(src_dna_obj._reader)

        dst_dna_obj = DNAReader.read(dst_dna_path, Layer.all)
        dst_calib_reader = dnacalib2.DNACalibDNAReader(dst_dna_obj._reader)

        if self.joint_xforms_checkbox.isChecked():
            mhJoints.merge_joint_neutral_xforms(src_calib_reader, dst_calib_reader)

        if self.vertex_positions_checkbox.isChecked():
            mhMesh.merge_meshes_positions(src_dna_obj, src_calib_reader, dst_dna_obj, dst_calib_reader)

        if self.calculate_lods_checkbox.isChecked():
            mhMesh.calculate_lods(dst_dna_obj, dst_calib_reader)

        if self.poses_checkbox.isChecked():
            pose_manager = mhProject.PoseManager()
            poses = mhBehaviour.get_all_poses(src_calib_reader, pose_manager)

            mhBehaviour.save_dna(
                dst_calib_reader,
                output_dna_path,
                validate=True,
                as_json=self.json_checkbox.isChecked(),
                poses=poses,
            )

        else:
            mhUtils.save_dna(
                dst_calib_reader,
                output_dna_path,
                validate=False,
                as_json=self.json_checkbox.isChecked()
            )

        status = dna.Status.get().message

        if not dna.Status.isOk():
            self.error(QtWidgets.QMessageBox.Ok)
            return False

        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "Dna file exported:\n{}".format(output_dna_path),
            QtWidgets.QMessageBox.Ok
        )

        self.accept()

        return True


class DnaBakeRigWidget(mhWidgets.Tab):
    class UtilsMenu(QtWidgets.QMenu):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.setTitle("utils")

            empty_icon = QtGui.QIcon()

            self.inspect_action = QtWidgets.QAction(empty_icon, 'inspect config', self)
            self.inspect_action.setStatusTip('Inspect bake config json file contents')
            self.addAction(self.inspect_action)

    def __init__(self, project, parent=None):
        super(DnaBakeRigWidget, self).__init__(project, parent=parent)

        self._create_menus()
        self._create_widgets()

    def refresh(self):
        self.dna_file_combo.refresh()

    def _create_menus(self):
        self.menubar = self.menuBar()

        # utils
        self.utils_menu = self.UtilsMenu(parent=self)
        self.menubar.addMenu(self.utils_menu)

        self.utils_menu.inspect_action.triggered.connect(self._inspect_clicked)

    def _create_widgets(self):

        self.dna_file_combo = mhWidgets.DnaPathManagerWidget(self.project, "dna file")

        self.tabs = QtWidgets.QTabWidget()

        # build
        self.bake_tab = QtWidgets.QWidget()
        bake_lyt = QtWidgets.QVBoxLayout()
        self.bake_tab.setLayout(bake_lyt)

        self.build_label = QtWidgets.QLabel(
            "This process will take the 'live' metahuman rig and bake it fully to blendshapes.\n"
            "\n"
            "All poses and combos present in the dna file will be baked and rig logic reproduced.\n"
            "\n"
            "Use the bake config file to add new combos or extra shapes, in-betweens, etc.\n"
            "\n"
            "Joints used to drive the other meshes such as the teeth and eyes will be kept,\n"
            "all redundant joints are deleted, unless specified in the config file.\n"
            "\n"
            "Neck corrective readers and targets are also added, as defined by the config file.\n"
        )

        bake_lyt.addWidget(self.build_label)

        self.bake_shapes_checkbox = QtWidgets.QCheckBox("bake shapes")
        self.calculate_psd_deltas_checkbox = QtWidgets.QCheckBox("calculate psd deltas")
        self.connect_shapes_checkbox = QtWidgets.QCheckBox("connect shapes")
        self.connect_joints_checkbox = QtWidgets.QCheckBox("connect joints")
        self.optimise_checkbox = QtWidgets.QCheckBox("optimise")
        # self.cleanup_checkbox = QtWidgets.QCheckBox("cleanup")
        self.delete_targets_checkbox = QtWidgets.QCheckBox("delete targets")
        self.delete_unused_checkbox = QtWidgets.QCheckBox("delete unused")
        self.use_combo_network_checkbox = QtWidgets.QCheckBox("use combo network")
        self.use_sdks_checkbox = QtWidgets.QCheckBox("use SDKs")

        for checkbox in [
            self.bake_shapes_checkbox,
            self.calculate_psd_deltas_checkbox,
            self.connect_shapes_checkbox,
            self.connect_joints_checkbox,
            self.optimise_checkbox,
            # self.cleanup_checkbox,
            self.delete_targets_checkbox,
            self.delete_unused_checkbox,
            self.use_combo_network_checkbox,
            self.use_sdks_checkbox,
        ]:
            checkbox.setChecked(True)
            bake_lyt.addWidget(checkbox)

        # build btn
        self.build_btn = QtWidgets.QPushButton("Build")
        self.build_btn.clicked.connect(self._build_clicked)

        bake_lyt.addWidget(self.build_btn)
        bake_lyt.addStretch()

        self.tabs.addTab(self.bake_tab, "build")

        # edit tab
        self.edit_tab = QtWidgets.QWidget()
        edit_lyt = QtWidgets.QVBoxLayout()
        self.edit_tab.setLayout(edit_lyt)

        self.edit_label = QtWidgets.QLabel(
            "If you need to make changes to the bake config, such as adding new shapes and combos,\n"
            "first 'disconnect' to delete existing rig logic, then 'reconnect' to create updated rig logic.\n"
            "This will also add any new targets to the blendshape node(s)\n"
        )

        edit_lyt.addWidget(self.edit_label)

        # disconnect group box
        self.disconnect_group_box = QtWidgets.QGroupBox("disconnect")

        disconnect_lyt = QtWidgets.QVBoxLayout()
        self.disconnect_group_box.setLayout(disconnect_lyt)

        self.disconnect_targets_checkbox = QtWidgets.QCheckBox("disconnect targets")
        self.disconnect_joints_checkbox = QtWidgets.QCheckBox("disconnect joints")
        self.delete_combo_network_checkbox = QtWidgets.QCheckBox("delete combo network")

        self.disconnect_targets_checkbox.setChecked(True)
        self.disconnect_joints_checkbox.setChecked(True)
        self.delete_combo_network_checkbox.setChecked(True)

        # disconnect btn
        self.disconnect_btn = QtWidgets.QPushButton("disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect_clicked)

        disconnect_lyt.addWidget(self.disconnect_targets_checkbox)
        disconnect_lyt.addWidget(self.disconnect_joints_checkbox)
        disconnect_lyt.addWidget(self.delete_combo_network_checkbox)
        disconnect_lyt.addWidget(self.disconnect_btn)

        # reconnect group box
        self.reconnect_group_box = QtWidgets.QGroupBox("reconnect")

        reconnect_lyt = QtWidgets.QVBoxLayout()
        self.reconnect_group_box.setLayout(reconnect_lyt)

        # add missing
        self.add_missing_targets_checkbox = QtWidgets.QCheckBox("add missing targets")
        self.reconnect_combo_network_checkbox = QtWidgets.QCheckBox("use combo network")
        self.reconnect_targets_checkbox = QtWidgets.QCheckBox("reconnect targets")
        self.reconnect_joints_checkbox = QtWidgets.QCheckBox("reconnect joints")
        self.reconnect_baked_joints_only_checkbox = QtWidgets.QCheckBox("baked joints only")
        self.reconnect_use_sdks_checkbox = QtWidgets.QCheckBox("use SDKs")

        # reconnect btn
        self.reconnect_btn = QtWidgets.QPushButton("Reconnect")
        self.reconnect_btn.clicked.connect(self._reconnect_clicked)

        for checkbox in [
            self.add_missing_targets_checkbox,
            self.reconnect_combo_network_checkbox,
            self.reconnect_targets_checkbox,
            self.reconnect_joints_checkbox,
            self.reconnect_baked_joints_only_checkbox,
            self.reconnect_use_sdks_checkbox
        ]:
            checkbox.setChecked(True)
            reconnect_lyt.addWidget(checkbox)

        reconnect_lyt.addWidget(self.reconnect_btn)

        # edit layout
        edit_lyt.addWidget(self.disconnect_group_box)
        edit_lyt.addWidget(self.reconnect_group_box)
        edit_lyt.addStretch()

        self.tabs.addTab(self.edit_tab, "edit")
        self.tabs.setCurrentIndex(0)

        # utils tab
        self.utils_tab = QtWidgets.QWidget()
        utils_lyt = QtWidgets.QVBoxLayout()
        self.utils_tab.setLayout(utils_lyt)

        # bake driven group box
        self.bake_driven_group_box = QtWidgets.QGroupBox("bake driven")

        bake_driven_lyt = QtWidgets.QVBoxLayout()
        self.bake_driven_group_box.setLayout(bake_driven_lyt)

        self.driver_bs_node_widget = mhWidgets.NodeLineEdit(
            default="head_lod0_blendShape", label="driver blendshape", label_width=100
        )

        self.driven_mesh_widget = mhWidgets.NodeLineEdit(
            label="driven mesh", label_width=100
        )

        self.bake_driven_targets_only_checkbox = QtWidgets.QCheckBox("targets only")
        self.bake_driven_skip_static_checkbox = QtWidgets.QCheckBox("skip static")
        self.bake_driven_connect_checkbox = QtWidgets.QCheckBox("connect")
        self.bake_driven_cleanup_checkbox = QtWidgets.QCheckBox("cleanup")

        self.bake_driven_skip_static_checkbox.setChecked(True)
        self.bake_driven_connect_checkbox.setChecked(True)
        self.bake_driven_cleanup_checkbox.setChecked(True)

        self.bake_driven_btn = QtWidgets.QPushButton("bake driven")
        self.bake_driven_btn.clicked.connect(self._bake_driven_clicked)

        bake_driven_lyt.addWidget(self.driver_bs_node_widget)
        bake_driven_lyt.addWidget(self.driven_mesh_widget)
        bake_driven_lyt.addWidget(self.bake_driven_targets_only_checkbox)
        bake_driven_lyt.addWidget(self.bake_driven_skip_static_checkbox)
        bake_driven_lyt.addWidget(self.bake_driven_connect_checkbox)
        bake_driven_lyt.addWidget(self.bake_driven_cleanup_checkbox)
        bake_driven_lyt.addWidget(self.bake_driven_btn)

        # extract pose correctives group box
        self.extract_correctives_group_box = QtWidgets.QGroupBox("extract correctives")

        extract_correctives_lyt = QtWidgets.QVBoxLayout()
        self.extract_correctives_group_box.setLayout(extract_correctives_lyt)

        self.correctives_mesh_widget = mhWidgets.NodeLineEdit(
            default="head_lod0_mesh", label="mesh", label_width=100
        )

        self.correctives_bs_node_widget = mhWidgets.NodeLineEdit(
            default="head_lod0_blendShape", label="blendshape", label_width=100
        )

        self.correctives_skinned_mesh_widget = mhWidgets.NodeLineEdit(
            label="skinned mesh", label_width=100
        )

        self.extract_correctives_cleanup_checkbox = QtWidgets.QCheckBox("cleanup")

        self.extract_correctives_cleanup_checkbox.setChecked(True)

        self.extract_correctives_btn = QtWidgets.QPushButton("extract correctives")
        self.extract_correctives_btn.clicked.connect(self._extract_correctives_clicked)

        extract_correctives_lyt.addWidget(self.correctives_mesh_widget)
        extract_correctives_lyt.addWidget(self.correctives_bs_node_widget)
        extract_correctives_lyt.addWidget(self.correctives_skinned_mesh_widget)
        extract_correctives_lyt.addWidget(self.extract_correctives_cleanup_checkbox)
        extract_correctives_lyt.addWidget(self.extract_correctives_btn)

        # utils layout
        utils_lyt.addWidget(self.bake_driven_group_box)
        utils_lyt.addWidget(self.extract_correctives_group_box)
        utils_lyt.addStretch()

        self.tabs.addTab(self.utils_tab, "utils")

        # set default tab
        self.tabs.setCurrentIndex(0)

        # create layout
        lyt = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(lyt)

        lyt.addWidget(self.dna_file_combo)
        lyt.addWidget(self.tabs)

    def _inspect_clicked(self):
        """
        """
        # get paths
        dna_path = self.dna_file_combo.get_path()
        bake_config_file = self.project.bake_config_path

        # check we have paths
        if not dna_path:
            self.error("No source DNA path given")
            return False

        if not bake_config_file:
            self.error("No bake config path given")
            return False

        # load dna data
        pose_manager = mhBehaviour.load_poses_from_dna(dna_path)

        # load config
        bake_config = mhBakeRig.BakeConfig.load(bake_config_file)
        new_poses, new_combos = bake_config.update_pose_manager(pose_manager)

        new_targets = list(bake_config.shapes)
        new_targets += [combo_pose.pose.name for combo_pose in new_combos]

        target_text = (
            "meshes: \n{}  \n\n"
            "\n"
            "total targets: {}\n\n"
            "additional shapes: {}\n\n"
            "readers: {}\n\n"
            "new targets:\n  "
            "{}\n"
            "\n"
        ).format(
            "\n  ".join([a for a, b in bake_config.mesh_blendshapes]),
            len(new_targets),
            len(bake_config.shapes),
            len(bake_config.readers),
            "\n  ".join(new_targets)
        )

        dialog = mhWidgets.DebugDialog(target_text, parent=self)
        dialog.setWindowTitle("Bake debug")
        dialog.exec_()

        return True

    def _build_clicked(self):

        # get paths
        dna_path = self.dna_file_combo.get_path()
        bake_config_file = self.project.bake_config_path

        # check we have paths
        if not dna_path:
            self.error("No source DNA path given")
            return False

        if not bake_config_file:
            self.error("No bake config path given")
            return False

        # confirm with user
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "This will bake the rig in the scene as defined by dna file and config:\n\n{}\n\n{}\n\nContinue?".format(
                dna_path, bake_config_file
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return False

        pose_manager = mhBehaviour.load_poses_from_dna(dna_path)

        mhBakeRig.bake_rig(
            pose_manager,
            bake_config_file,
            bake_shapes=self.bake_shapes_checkbox.isChecked(),
            calculate_combos=self.calculate_psd_deltas_checkbox.isChecked(),
            connect_shapes=self.connect_shapes_checkbox.isChecked(),
            connect_joints=self.connect_joints_checkbox.isChecked(),
            optimise=self.optimise_checkbox.isChecked(),
            delete_targets=self.delete_targets_checkbox.isChecked(),
            delete_unused=self.delete_unused_checkbox.isChecked(),
            expressions_node="CTRL_expressions",
            use_combo_network=self.use_combo_network_checkbox.isChecked(),
            use_sdks=self.use_sdks_checkbox.isChecked(),
        )

        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "Shape bake complete",
            QtWidgets.QMessageBox.Ok
        )

        return True

    def _disconnect_clicked(self):
        try:
            mhBakeRig.disconnect(
                self.project.bake_config_path,
                disconnect_targets=self.disconnect_targets_checkbox.isChecked(),
                disconnect_joints=self.disconnect_joints_checkbox.isChecked(),
                delete_combo_network=self.delete_combo_network_checkbox.isChecked(),
            )

            QtWidgets.QMessageBox.information(
                self,
                "Success",
                "Disconnect complete",
                QtWidgets.QMessageBox.Ok
            )
        except Exception as err:
            self.error(err)

    def _reconnect_clicked(self):

        # get paths
        dna_path = self.dna_file_combo.get_path()
        bake_config_file = self.project.bake_config_path

        # check we have paths
        if not dna_path:
            self.error("No source DNA path given")
            return False

        if not bake_config_file:
            self.error("No bake config path given")
            return False

        # confirm with user
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "This will reconnect shapes in the scene as defined by dna file and config:\n\n{}\n\n{}\nContinue?".format(
                dna_path, bake_config_file
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return False

        # load data
        pose_manager = mhBehaviour.load_poses_from_dna(dna_path)

        # reconnect
        try:
            mhBakeRig.reconnect(
                pose_manager,
                bake_config_file,
                expressions_node="CTRL_expressions",
                use_combo_network=self.reconnect_combo_network_checkbox.isChecked(),
                add_missing_targets=self.add_missing_targets_checkbox.isChecked(),
                reconnect_joints=self.reconnect_joints_checkbox.isChecked(),
                baked_joints_only=self.reconnect_baked_joints_only_checkbox.isChecked(),
                reconnect_targets=self.reconnect_targets_checkbox.isChecked(),
                use_sdks=self.reconnect_use_sdks_checkbox.isChecked(),
            )

            QtWidgets.QMessageBox.information(
                self,
                "Success",
                "Reconnect complete",
                QtWidgets.QMessageBox.Ok
            )

        except Exception as err:
            self.error(err)

        return True

    def _bake_driven_clicked(self):
        mhBlendshape.bake_blendshape_driven_mesh(
            self.driver_bs_node_widget.node,
            self.driven_mesh_widget.node,
            cleanup=self.bake_driven_cleanup_checkbox.isChecked(),
            skip_static=self.bake_driven_skip_static_checkbox.isChecked(),
            connect=self.bake_driven_connect_checkbox.isChecked(),
            targets_only=self.bake_driven_targets_only_checkbox.isChecked()
        )

    def _extract_correctives_clicked(self):

        # get paths
        dna_path = self.dna_file_combo.get_path()
        bake_config_file = self.project.bake_config_path

        # check we have paths
        if not dna_path:
            self.error("No source DNA path given")
            return False

        if not bake_config_file:
            self.error("No bake config path given")
            return False

        # confirm with user
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "This will extract correctives in the scene as defined by dna file, config and skinned mesh:\n\n{}\n\n{}\n\n{}\n\nContinue?".format(
                dna_path, bake_config_file, self.correctives_skinned_mesh_widget.node
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return False

        try:

            pose_manager = mhBehaviour.load_poses_from_dna(dna_file)

            mhBakeRig.extract_pose_correctives(
                pose_manager,
                bake_config_file,
                self.correctives_mesh_widget.node,
                self.correctives_bs_node_widget.node,
                self.correctives_skinned_mesh_widget.node,
                cleanup=self.extract_correctives_cleanup_checkbox.isChecked()
            )

            QtWidgets.QMessageBox.information(
                self,
                "Success",
                "Extract correctives complete",
                QtWidgets.QMessageBox.Ok
            )

        except Exception as err:
            self.error(err)

        return True


class DnaSculptWidget(mhWidgets.Tab):
    def __init__(self, project, parent=None):
        super(DnaSculptWidget, self).__init__(project, parent=parent)

        self.create_widgets()

    def create_widgets(self):

        # IO
        self.io_box = QtWidgets.QGroupBox("IO")

        # export objs
        self.export_objs_btn = QtWidgets.QPushButton("export objs")
        self.export_objs_btn.clicked.connect(self._export_objs_clicked)

        # import objs (with prefix)
        self.import_prefix = mhWidgets.LabelledLineEdit("import prefix", default="sculpt_")
        self.import_objs_btn = QtWidgets.QPushButton("import objs")
        self.import_objs_btn.clicked.connect(self._import_objs_clicked)

        # ingest sculpts
        self.bs_node_widget = mhWidgets.NodeLineEdit(
            default="head_lod0_mesh_blendShape",
            label="blendShape"
        )

        self.bs_node_widget.label.setFixedWidth(100)

        self.ingest_sculpts_btn = QtWidgets.QPushButton("ingest sculpts")
        self.ingest_sculpts_btn.clicked.connect(self._ingest_sculpts_clicked)

        # IO lyt
        io_lyt = QtWidgets.QVBoxLayout()
        self.io_box.setLayout(io_lyt)

        io_lyt.addWidget(self.import_prefix)
        io_lyt.addWidget(self.bs_node_widget)
        io_lyt.addWidget(self.export_objs_btn)
        io_lyt.addWidget(self.import_objs_btn)
        io_lyt.addWidget(self.ingest_sculpts_btn)

        # proxy combos
        self.proxy_combos_box = QtWidgets.QGroupBox("Proxy Combos")

        self.proxy_combo_label = QtWidgets.QLabel(
            "Select two or more targets in the shape editor and click 'Create'\n\n"
            "This will combine the targets into a single target on a new mesh and a sculpt target to do your work.\n\n"
            "Once you are done sculpting, select the proxy combo mesh and click 'Apply'\n\n"
            "This will divide the sculpt delta between the original targets based on their contribution to the combined target\n"
            "then add the resulting deltas on top of the original targets."
        )

        self.create_proxy_combo_btn = QtWidgets.QPushButton("Create")
        self.create_proxy_combo_btn.clicked.connect(self._create_proxy_combo_clicked)

        self.apply_proxy_combo_btn = QtWidgets.QPushButton("Apply")
        self.apply_proxy_combo_btn.clicked.connect(self._apply_proxy_combo_clicked)

        self.meta_data_btn = QtWidgets.QPushButton("meta data")
        self.meta_data_btn.clicked.connect(self._meta_data_clicked)

        btn_lyt = QtWidgets.QHBoxLayout()
        btn_lyt.addWidget(self.create_proxy_combo_btn)
        btn_lyt.addWidget(self.apply_proxy_combo_btn)
        btn_lyt.addWidget(self.meta_data_btn)

        proxy_combo_lyt = QtWidgets.QVBoxLayout()
        proxy_combo_lyt.addWidget(self.proxy_combo_label)
        proxy_combo_lyt.addLayout(btn_lyt)

        self.proxy_combos_box.setLayout(proxy_combo_lyt)

        # batch proxy combos
        self.batch_proxy_combos_box = QtWidgets.QGroupBox("Batch Proxy Combos")

        self.batch_proxy_combo_label = QtWidgets.QLabel(
            "Batch create or apply proxy combos from config json file\n"
            "An example config file can be found here: brenmeta/data/configs/example_proxy_combo_config.json"
        )

        self.batch_proxy_combo_create_widget = mhWidgets.PathOpenWidget("Config")
        self.batch_proxy_combo_create_widget.filter = "json files (*.json)"

        self.match_threshold_spin = mhWidgets.LabelledDoubleSpinBox(
            "match threshold", label_width=100, default=0.01, minimum=0.0, maximum=10.0
        )

        self.batch_create_proxy_combo_btn = QtWidgets.QPushButton("Create")
        self.batch_create_proxy_combo_btn.clicked.connect(self._batch_create_proxy_combos)

        self.batch_apply_proxy_combo_btn = QtWidgets.QPushButton("Apply")
        self.batch_apply_proxy_combo_btn.clicked.connect(self._batch_apply_proxy_combos)

        btn_lyt = QtWidgets.QHBoxLayout()
        btn_lyt.addWidget(self.batch_create_proxy_combo_btn)
        btn_lyt.addWidget(self.batch_apply_proxy_combo_btn)

        proxy_combo_lyt = QtWidgets.QVBoxLayout()
        proxy_combo_lyt.addWidget(self.batch_proxy_combo_label)
        proxy_combo_lyt.addWidget(self.batch_proxy_combo_create_widget)
        proxy_combo_lyt.addWidget(self.match_threshold_spin)
        proxy_combo_lyt.addLayout(btn_lyt)

        self.batch_proxy_combos_box.setLayout(proxy_combo_lyt)

        # deltas
        self.deltas_box = QtWidgets.QGroupBox("Deltas")

        self.deltas_label = QtWidgets.QLabel(
            "Utilities for directly manipulating deltas of selected shape editor targets"
        )

        self.add_deltas_btn = QtWidgets.QPushButton("Add")
        self.add_deltas_btn.clicked.connect(self._add_deltas_clicked)

        self.subtract_deltas_btn = QtWidgets.QPushButton("Subtract")
        self.subtract_deltas_btn.clicked.connect(self._subtract_deltas_clicked)

        self.reset_deltas_btn = QtWidgets.QPushButton("Reset")
        self.reset_deltas_btn.clicked.connect(self._reset_deltas_clicked)

        deltas_btn_lyt = QtWidgets.QHBoxLayout()
        deltas_btn_lyt.addWidget(self.add_deltas_btn)
        deltas_btn_lyt.addWidget(self.subtract_deltas_btn)
        deltas_btn_lyt.addWidget(self.reset_deltas_btn)

        deltas_lyt = QtWidgets.QVBoxLayout()
        deltas_lyt.addWidget(self.deltas_label)
        deltas_lyt.addLayout(deltas_btn_lyt)

        self.deltas_box.setLayout(deltas_lyt)

        # main layout
        lyt = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(lyt)

        lyt.addWidget(self.io_box)
        lyt.addWidget(self.proxy_combos_box)
        lyt.addWidget(self.batch_proxy_combos_box)
        lyt.addWidget(self.deltas_box)
        lyt.addStretch()

    def _export_objs_clicked(self):
        meshes = cmds.ls(sl=True, type="transform")

        if not meshes:
            self.error("Please selected meshes to export")
            return False

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Export Folder",
            None,
        )

        if not path:
            return False

        mhMayaUtils.export_meshes_to_objs(
            meshes, path
        )

        return True

    def _import_objs_clicked(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Import Folder",
            None,
        )

        if not path:
            return False

        mhMayaUtils.import_objs(path, prefix=self.import_prefix.text)

        return True

    def _ingest_sculpts_clicked(self):
        sculpts = cmds.ls(sl=True, type="transform")

        if not sculpts:
            self.error("Please selected sculpts to ingest")
            return False

        prefix = self.import_prefix.text

        # if prefix:
        #     prefix += "_"

        bs_node = self.bs_node_widget.node

        if not cmds.objExists(bs_node):
            self.error("blendshape node not found: {}".format(bs_node))
            return False

        mhBlendshape.apply_sculpts(
            bs_node,
            sculpts,
            prefix,
            rebuild=True,
        )

        return True

    def _create_proxy_combo_clicked(self):
        mhBlendshape.create_proxy_combo_sl()

    def _apply_proxy_combo_clicked(self):
        mhBlendshape.apply_proxy_combo_sl()

    def _batch_create_proxy_combos(self):
        config_file = self.batch_proxy_combo_create_widget.path

        if not os.path.exists(config_file):
            self.error("Config file not found: {}".format(config_file))

        mhBlendshape.batch_create_proxy_combos(config_file)

        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "Proxy Combo batch complete",
            QtWidgets.QMessageBox.Ok
        )

    def _batch_apply_proxy_combos(self):
        config_file = self.batch_proxy_combo_create_widget.path

        if not os.path.exists(config_file):
            self.error("Config file not found: {}".format(config_file))

        mhBlendshape.batch_apply_proxy_combos(
            config_file,
            match_threshold=self.match_threshold_spin.spin_box.value(),
        )

        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "Proxy Combo batch complete",
            QtWidgets.QMessageBox.Ok
        )

    def _add_deltas_clicked(self):
        mhBlendshape.add_deltas_sl()

    def _subtract_deltas_clicked(self):
        mhBlendshape.subtract_deltas_sl()

    def _reset_deltas_clicked(self):
        mhBlendshape.reset_target_sl()

    def _meta_data_clicked(self):
        mhBlendshape.print_selected_shape_editor_targets(
            as_list=True, target_weights=True
        )


class DnaModWidget(QtWidgets.QMainWindow):
    """TODO warning for maya 2023+ about skincluster backward incompatability
    """

    TITLE = "MetaHuman DNA Modification Tool"

    class FileMenu(QtWidgets.QMenu):
        """File menu
        """

        def __init__(self, parent=None):
            super(DnaModWidget.FileMenu, self).__init__(parent=parent)

            self.setTitle("File")

            file_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_FileIcon
            )

            open_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_DialogOpenButton
            )

            save_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_DialogSaveButton
            )

            reload_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_BrowserReload
            )

            self.new_action = QtWidgets.QAction(file_icon, 'New', self)
            self.new_action.setStatusTip('New')
            self.addAction(self.new_action)

            self.open_action = QtWidgets.QAction(open_icon, 'Open', self)
            self.open_action.setStatusTip('Open json file')
            self.addAction(self.open_action)

            self.save_action = QtWidgets.QAction(save_icon, 'Save', self)
            self.save_action.setStatusTip('Save json file')
            self.addAction(self.save_action)

            self.save_as_action = QtWidgets.QAction(save_icon, 'Save As', self)
            self.save_as_action.setStatusTip('Save json file as')
            self.addAction(self.save_as_action)

            self.addSeparator()

    class UtilsMenu(QtWidgets.QMenu):
        """Utils menu
        """

        def __init__(self, parent=None):
            super(DnaModWidget.UtilsMenu, self).__init__(parent=parent)

            self.setTitle("Utils")

            file_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_FileIcon
            )

            open_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_DialogOpenButton
            )

            save_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_DialogSaveButton
            )

            reload_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_BrowserReload
            )

            self.merge_action = QtWidgets.QAction(file_icon, 'Merge DNA', self)
            self.merge_action.setStatusTip('Merge dna files')
            self.merge_action.triggered.connect(self._merge)
            self.addAction(self.merge_action)

            self.addSection("animation")

            self.tech_rom_action = QtWidgets.QAction(file_icon, 'Create Tech ROM', self)
            self.tech_rom_action.triggered.connect(self._tech_rom)
            self.addAction(self.tech_rom_action)

            self.reset_anim_action = QtWidgets.QAction(file_icon, 'Reset anim', self)
            self.reset_anim_action.triggered.connect(self._reset_anim)
            self.addAction(self.reset_anim_action)

            self.connect_boards_action = QtWidgets.QAction(file_icon, 'Connect control boards', self)
            self.connect_boards_action.triggered.connect(self._connect_control_boards)
            self.addAction(self.connect_boards_action)

            self.disconnect_boards_action = QtWidgets.QAction(file_icon, 'Disconnect control boards', self)
            self.disconnect_boards_action.triggered.connect(self._disconnect_control_boards)
            self.addAction(self.disconnect_boards_action)

        def _merge(self):
            dialog = DnaMergeDialog(
                self.parent().project, parent=self.parent()
            )

            dialog.open()

        def _tech_rom(self):
            dialog = TechRomDialog(
                self.parent().project, parent=self.parent()
            )

            dialog.show()

        def _reset_anim(self):
            mhAnimUtils.reset_control_board_anim_sl()

        def _connect_control_boards(self):
            dialog = ConnectControlBoardsDialog(
                self.parent().project, parent=self.parent()
            )

            dialog.show()

        def _disconnect_control_boards(self):
            dialog = DisconnectControlBoardsDialog(
                self.parent().project, parent=self.parent()
            )

            dialog.show()

    def __init__(self, parent=None):
        super(DnaModWidget, self).__init__(parent=parent)

        self.project = mhProject.Project(DEFAULT_DNA_DATA_DIR)

        self.setWindowTitle(self.TITLE)

        self.menubar = self.menuBar()

        # file menu
        self.file_menu = self.FileMenu(parent=self)
        self.menubar.addMenu(self.file_menu)

        self.file_menu.new_action.triggered.connect(self.new)
        self.file_menu.open_action.triggered.connect(self.open)
        self.file_menu.save_action.triggered.connect(self.save)
        self.file_menu.save_as_action.triggered.connect(self.save_as)

        # utils menu
        self.utils_menu = self.UtilsMenu(parent=self)
        self.menubar.addMenu(self.utils_menu)

        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        self.project_widget = ProjectWidget(self.project)
        self.build_widget = DnaBuildWidget(self.project)
        self.transfer_widget = DnaTransferWidget(self.project)
        self.poses_widget = PosesTab(self.project)
        self.shape_bake_widget = DnaBakeRigWidget(self.project)
        self.sculpt_widget = DnaSculptWidget(self.project)

        self.tabs.addTab(self.project_widget, "project")
        self.tabs.addTab(self.build_widget, "build")
        self.tabs.addTab(self.transfer_widget, "transfer")
        self.tabs.addTab(self.poses_widget, "poses")
        self.tabs.addTab(self.shape_bake_widget, "bake")
        self.tabs.addTab(self.sculpt_widget, "sculpt")

        self.project_widget.PATHS_CHANGED.connect(self.refresh)

        self.refresh()

    def log(self, msg):
        LOG.info(msg)

    def refresh(self):
        for widget in [
            self.project_widget,
            self.build_widget,
            self.transfer_widget,
            self.poses_widget,
            self.shape_bake_widget,
            self.sculpt_widget,
        ]:
            widget.refresh()

    def update_title(self):
        title = self.TITLE

        if self.project.current_file:
            title = "{} - {}".format(title, self.project.current_file)

        self.setWindowTitle(title)

        return True

    def new(self):
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "Reset all project data?",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return

        self.project.reset(DEFAULT_DNA_DATA_DIR)
        self.update_title()
        self.refresh()

    def open(self):
        file_path, file_type = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open File",
            self.project.current_file,
            "*.json"
        )

        if file_path == "":
            return None

        try:
            self.project.read(file_path)
            self.update_title()
            self.refresh()
            return True
        except Exception as err:
            msg = "Failed to open file: {}\n\nError:\n{}\n\nSee log for details".format(file_path, err)

            print(traceback.format_exc())

            LOG.critical(str(err))

            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                str(err),
                QtWidgets.QMessageBox.Ok
            )

            return False

    def save(self):
        if self.project.current_file is None:
            return self.save_as()
        else:

            try:
                self.project.write(self.project.current_file)
                self.log("file saved: {}".format(self.project.current_file))
                return True
            except Exception as err:

                print(traceback.format_exc())

                msg = "Failed to save file: {}\n\nError:\n{}\n\nSee log for details".format(
                    self.project.current_file, err
                )

                return False

    def save_as(self):
        # get file path from user
        file_path, file_type = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save file",
            self.project.current_file,
            "*.json"
        )

        if file_path == "":
            return

        if not file_path.endswith(".json"):
            file_path = "{}.json".format(file_path)

        self.project.current_file = file_path

        self.save()
        self.update_title()

    @classmethod
    def create(cls, width=800, height=400, show=True):

        maya_main_window_ptr = OpenMayaUI.MQtUtil.mainWindow()
        maya_main_window = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)

        widget = cls(parent=maya_main_window)

        if show:
            widget.show()

        geometry = widget.geometry()

        if width:
            geometry.setWidth(width)

        if height:
            geometry.setHeight(height)

        widget.setGeometry(geometry)

        return widget
