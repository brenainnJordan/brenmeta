"""

"""

import os

from maya import cmds
from maya import OpenMayaUI
from maya.api import OpenMaya

from Qt import QtCore
from Qt import QtWidgets

try:
    from shiboken2 import wrapInstance   # Maya with PySide2
except ImportError:
    from shiboken6 import wrapInstance   # Maya with PySide6

import dna
import dnacalib2
import mh_character_assembler

from brenmeta.core import mhCore
from brenmeta.core import mhWidgets
from brenmeta.dna2 import mhSrc
from brenmeta.dna2 import mhUtils
# from brenmeta.dna1 import mhSrc
# from brenmeta.dna1 import mhUtils
# from brenmeta.dna1 import mhBehaviour
# from brenmeta.dna1 import mhUeUtils
# from brenmeta.dna1 import mhMesh
# from brenmeta.dna1 import mhJoints
from brenmeta.mh import mhFaceMaterials, mhFaceJoints
from brenmeta.mh import mhFaceMeshes
from brenmeta.maya import mhAnimUtils

LOG = mhCore.get_basic_logger(__name__)


class DnaTransferWidget(QtWidgets.QWidget):

    def __init__(self, path_manager, *args, **kwargs):
        super(DnaTransferWidget, self).__init__(*args, **kwargs)

        self.path_manager = path_manager

        lyt = QtWidgets.QVBoxLayout()
        self.setLayout(lyt)

        # transfer meshes
        self.transfer_meshes_group_box = QtWidgets.QGroupBox("transfer meshes")

        meshes_lyt = QtWidgets.QVBoxLayout()
        self.transfer_meshes_group_box.setLayout(meshes_lyt)

        # TODO more options

        self.eyeballs_checkbox = QtWidgets.QCheckBox("eyeballs")
        self.eyelashes_checkbox = QtWidgets.QCheckBox("eyelashes")
        self.eyewet_checkbox = QtWidgets.QCheckBox("eyewet")
        # self.eye_pivots_checkbox = QtWidgets.QCheckBox("Recalculate eye pivots")
        self.inner_mouth_checkbox = QtWidgets.QCheckBox("inner mouth")
        self.cleanup_checkbox = QtWidgets.QCheckBox("cleanup")

        for checkbox in [
            self.eyeballs_checkbox,
            self.eyelashes_checkbox,
            self.eyewet_checkbox,
            # self.eye_pivots_checkbox,
            self.inner_mouth_checkbox,
            self.cleanup_checkbox,
        ]:
            checkbox.setChecked(True)
            # checkbox.setFixedWidth(80)
            meshes_lyt.addWidget(checkbox)

        self.transfer_face_meshes_btn = QtWidgets.QPushButton("transfer face meshes")
        self.transfer_face_meshes_btn.clicked.connect(self.transfer_face_meshes)

        meshes_lyt.addWidget(self.transfer_face_meshes_btn)

        # transfer joints
        self.transfer_joints_group_box = QtWidgets.QGroupBox("transfer joints")

        joints_lyt = QtWidgets.QVBoxLayout()
        self.transfer_joints_group_box.setLayout(joints_lyt)

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

        # update dna
        self.update_dna_group_box = QtWidgets.QGroupBox("update dna")

        update_dna_lyt = QtWidgets.QVBoxLayout()
        self.update_dna_group_box.setLayout(update_dna_lyt)

        self.input_dna_combo = QtWidgets.QComboBox()

        self.scale_spin = mhWidgets.LabelledDoubleSpinBox("scale", label_width=80, spin_box_width=80, height=30,
                                                          default=1.0)
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

        update_dna_lyt.addWidget(self.input_dna_combo)
        update_dna_lyt.addWidget(self.scale_spin)
        update_dna_lyt.addWidget(self.update_mesh_checkbox)
        update_dna_lyt.addWidget(self.update_joint_xforms_checkbox)
        update_dna_lyt.addWidget(self.update_joint_list_checkbox)
        update_dna_lyt.addWidget(self.calculate_lods_checkbox)
        update_dna_lyt.addWidget(self.json_checkbox)
        update_dna_lyt.addWidget(self.update_btn)

        # main lyt
        lyt.addWidget(self.transfer_meshes_group_box)
        lyt.addWidget(self.transfer_joints_group_box)
        lyt.addWidget(self.update_dna_group_box)
        lyt.addStretch()

    def update_assets(self):
        self.input_dna_combo.clear()
        self.input_dna_combo.addItems(self.path_manager.get_dna_files())
        return True

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
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No update options checked",
                QtWidgets.QMessageBox.Ok
            )

            return

        # get path
        input_dna = str(self.input_dna_combo.currentText())

        input_dna_path = self.path_manager.get_path(input_dna)

        # check we have an input path
        if not input_dna_path:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No input DNA path given",
                QtWidgets.QMessageBox.Ok
            )

            return

        # check we have an output path
        if not self.path_manager.output_dna_path:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No output DNA path given",
                QtWidgets.QMessageBox.Ok
            )

            return

        # confirm with user
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "This will update input dna file:\n\n{}\n\nThen write output dna file to: \n\n{}\n\nContinue?".format(
                input_dna_path, self.path_manager.output_dna_path
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return None

        dna_obj = dna_viewer.DNA(input_dna_path)

        calib_reader = dnacalib.DNACalibDNAReader(dna_obj.reader)

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
            self.path_manager.output_dna_path,
            validate=False,
            as_json=self.json_checkbox.isChecked()
        )

        status = dna.Status.get().message

        if not dna.Status.isOk():
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                status,
                QtWidgets.QMessageBox.Ok
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                "Dna file exported:\n{}".format(self.path_manager.output_dna_path),
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

    def error(self, err):
        QtWidgets.QMessageBox.critical(
            self,
            "Error",
            str(err),
            QtWidgets.QMessageBox.Ok
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

        dna_obj = dna_viewer.DNA(dna_path)
        calib_reader = dnacalib.DNACalibDNAReader(dna_obj.reader)

        # mesh text
        mesh_fmt = "    {mesh_name}: {point_count} points, {blendshape_count} blendshape targets\n"

        mesh_txt = ""

        mesh_indices = mhMesh.get_mesh_indices(dna_obj, calib_reader, lod=lod)

        for mesh_index in mesh_indices:
            mesh_txt += mesh_fmt.format(
                mesh_name=dna_obj.meshes.names[mesh_index],
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
        blendshape_channel_inputs = calib_reader.getBlendShapeChannelInputIndices()

        columns_to_blendshapes = [""] * calib_reader.getJointColumnCount()

        for blendshape_channel_name, joint_column in zip(blendshape_channel_names, blendshape_channel_inputs):
            columns_to_blendshapes[joint_column] = blendshape_channel_name

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
            input_names = [columns_to_blendshapes[i] for i in psd_mapping[psd_output]]
            psd_text += "{}: {}\n".format(psd_name, input_names)

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


class DnaBuildWidget(QtWidgets.QWidget):

    def __init__(self, path_manager, *args, **kwargs):
        super(DnaBuildWidget, self).__init__(*args, **kwargs)

        self.path_manager = path_manager

        lyt = QtWidgets.QVBoxLayout()
        self.setLayout(lyt)

        # build
        self.build_group_box = QtWidgets.QGroupBox("build rig")

        build_lyt = QtWidgets.QVBoxLayout()
        self.build_group_box.setLayout(build_lyt)

        self.build_combo = QtWidgets.QComboBox()

        # TODO more options
        # self.full_rig_checkbox = QtWidgets.QCheckBox("full rig")

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

        self.inspect_btn = QtWidgets.QPushButton("Inspect")
        self.inspect_btn.setFixedHeight(30)
        self.inspect_btn.clicked.connect(self.inspect_dna)

        self.build_btn = QtWidgets.QPushButton("Build")
        self.build_btn.setFixedHeight(30)
        self.build_btn.clicked.connect(self.build_rig)

        build_lyt.addWidget(self.build_combo)
        build_lyt.addWidget(self.inspect_btn)
        build_lyt.addWidget(self.partial_rig_group_box)
        build_lyt.addWidget(self.build_btn)

        # utils
        self.utils_group_box = QtWidgets.QGroupBox("utils")

        utils_lyt = QtWidgets.QVBoxLayout()
        self.utils_group_box.setLayout(utils_lyt)

        self.set_look_btn = QtWidgets.QPushButton("Set joint look")
        self.set_look_btn.setFixedHeight(30)
        self.set_look_btn.clicked.connect(self.set_look)

        self.add_spine_btn = QtWidgets.QPushButton("Add spine joints")
        self.add_spine_btn.setFixedHeight(30)
        self.add_spine_btn.clicked.connect(self.add_spine)

        self.add_exp_btn = QtWidgets.QPushButton("Add expression attrs")
        self.add_exp_btn.setFixedHeight(30)
        self.add_exp_btn.clicked.connect(self.add_exp)

        self.prefix_btn = QtWidgets.QPushButton("Prefix meshes")
        self.prefix_btn.setFixedHeight(30)
        self.prefix_btn.clicked.connect(self.prefix_meshes)

        utils_lyt.addWidget(self.set_look_btn)
        utils_lyt.addWidget(self.add_spine_btn)
        utils_lyt.addWidget(self.add_exp_btn)
        utils_lyt.addWidget(self.prefix_btn)

        # materials
        self.materials_group_box = QtWidgets.QGroupBox("materials")

        materials_lyt = QtWidgets.QVBoxLayout()
        self.materials_group_box.setLayout(materials_lyt)

        self.import_materials_btn = QtWidgets.QPushButton("Import materials")
        self.import_materials_btn.setFixedHeight(30)
        self.import_materials_btn.clicked.connect(self.import_materials)

        self.reset_materials_btn = QtWidgets.QPushButton("Reset Materials")
        self.reset_materials_btn.setFixedHeight(30)
        self.reset_materials_btn.clicked.connect(self.reset_materials)

        self.lamberts_btn = QtWidgets.QPushButton("Create lamberts")
        self.lamberts_btn.setFixedHeight(30)
        self.lamberts_btn.clicked.connect(self.create_lamberts)

        self.create_lights_btn = QtWidgets.QPushButton("Create lights")
        self.create_lights_btn.setFixedHeight(30)
        self.create_lights_btn.clicked.connect(self.create_lights)

        self.repath_common_btn = QtWidgets.QPushButton("Repath Common")
        self.repath_common_btn.setFixedHeight(30)
        self.repath_common_btn.clicked.connect(self.repath_common)

        self.repath_asset_btn = QtWidgets.QPushButton("Repath Asset")
        self.repath_asset_btn.setFixedHeight(30)
        self.repath_asset_btn.clicked.connect(self.repath_asset)

        self.repath_widget = mhWidgets.RepathWidget()

        materials_lyt.addWidget(self.import_materials_btn)
        materials_lyt.addWidget(self.repath_common_btn)
        materials_lyt.addWidget(self.repath_asset_btn)
        materials_lyt.addWidget(self.reset_materials_btn)
        materials_lyt.addWidget(self.lamberts_btn)
        materials_lyt.addWidget(self.create_lights_btn)
        materials_lyt.addWidget(self.repath_widget)

        # main lyt
        lyt.addWidget(self.build_group_box)
        lyt.addWidget(self.utils_group_box)
        lyt.addWidget(self.materials_group_box)
        lyt.addStretch()

        # update drop down boxes
        self.update_assets()

    def update_assets(self):
        self.build_combo.clear()
        self.build_combo.addItems(self.path_manager.get_dna_files())
        return True

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
        mhUeUtils.create_materials()

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

    def error(self, err):
        QtWidgets.QMessageBox.critical(
            self,
            "Error",
            str(err),
            QtWidgets.QMessageBox.Ok
        )

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

    def inspect_dna(self, lod=0):
        build_mode = str(self.build_combo.currentText())

        dna_path = self.path_manager.get_path(build_mode)

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

        build_mode = str(self.build_combo.currentText())

        dna_path = self.path_manager.get_path(build_mode)

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
                self.path_manager.dna_assets_path,
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
                self.path_manager.dna_assets_path,
                add_joints=True,
                add_rig_logic=True,
                add_skin_cluster=True,
                add_blend_shapes=True,
                lod=None,
                scene_up="y",
            )

        return True


class DnaPosesModel(QtCore.QAbstractItemModel):
    HEADERS = ["", "pose", "shape"]

    def __init__(self, parent=None):
        super(DnaPosesModel, self).__init__(parent)
        self.poses = None

    def set_poses(self, poses):
        self.beginResetModel()
        self.poses = poses
        self.endResetModel()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):
        if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
            if orientation == QtCore.Qt.Horizontal:
                if section < len(self.HEADERS):
                    return self.HEADERS[section]

        return super(DnaPosesModel, self).headerData(section, orientation, role)

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

        if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
            if index.column() == 0:
                return pose.index
            if index.column() == 1:
                return pose.name
            if index.column() == 2:
                return pose.shape_name

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


class DnaPosesWidget(QtWidgets.QWidget):
    def __init__(self, path_manager, *args, **kwargs):
        super(DnaPosesWidget, self).__init__(*args, **kwargs)

        self.dna_obj = None
        self.calib_reader = None
        self.poses = None

        self.path_manager = path_manager

        self.create_widgets()

    def create_widgets(self):
        self.input_combo = QtWidgets.QComboBox()

        self.load_btn = QtWidgets.QPushButton("load poses")
        self.save_btn = QtWidgets.QPushButton("save output dna")

        self.load_btn.clicked.connect(self.load)
        self.save_btn.clicked.connect(self.save)

        self.path_line_edit = QtWidgets.QLineEdit()

        # self.model = QtCore.QStringListModel()
        self.model = DnaPosesModel()
        self.proxy_model = QtCore.QSortFilterProxyModel()

        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)

        # self.view = QtWidgets.QListView()
        self.view = QtWidgets.QTreeView()
        self.view.setModel(self.proxy_model)
        self.view.setSelectionMode(self.view.SelectionMode.ExtendedSelection)
        self.view.header().resizeSection(0, 50)
        self.view.header().resizeSection(1, 150)

        # selected
        self.selected_group_box = QtWidgets.QGroupBox("Selected")
        self.selected_lyt = QtWidgets.QVBoxLayout()
        self.selected_group_box.setLayout(self.selected_lyt)

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

        # selected lyt
        self.selected_lyt.addWidget(self.selected_scene_group_box)
        self.selected_lyt.addWidget(self.selected_data_group_box)

        # all
        self.all_group_box = QtWidgets.QGroupBox("All")
        self.all_lyt = QtWidgets.QVBoxLayout()
        self.all_group_box.setLayout(self.all_lyt)

        self.scale_all_poses_btn = QtWidgets.QPushButton("scale")

        self.scale_all_poses_btn.clicked.connect(self.scale_all_poses)

        self.all_lyt.addWidget(self.scale_all_poses_btn)

        # general layout
        self.input_lyt = QtWidgets.QHBoxLayout()
        self.input_lyt.addWidget(self.input_combo)
        self.input_lyt.addWidget(self.load_btn)

        self.view_btn_lyt = QtWidgets.QVBoxLayout()

        self.view_btn_lyt.addWidget(self.selected_group_box)
        self.view_btn_lyt.addWidget(self.all_group_box)
        self.view_btn_lyt.addStretch()

        self.view_lyt = QtWidgets.QHBoxLayout()

        self.view_lyt.addWidget(self.view)
        self.view_lyt.addLayout(self.view_btn_lyt)

        self.filter_line_edit = QtWidgets.QLineEdit()
        self.filter_line_edit.setFixedHeight(30)
        self.filter_line_edit.textChanged.connect(self.filter_changed)

        lyt = QtWidgets.QVBoxLayout()

        lyt.addLayout(self.input_lyt)
        lyt.addWidget(self.filter_line_edit)
        lyt.addLayout(self.view_lyt)
        lyt.addWidget(self.save_btn)

        self.setLayout(lyt)

        self.view.selectionModel().selectionChanged.connect(self.selection_changed)

    def update_assets(self):
        self.input_combo.clear()
        self.input_combo.addItems(self.path_manager.get_dna_files())
        return True

    def load(self):
        input_dna = self.input_combo.currentText()
        input_dna_path = self.path_manager.get_path(input_dna)

        # check we have an input path
        if not input_dna_path:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No DNA path given",
                QtWidgets.QMessageBox.Ok
            )

            return

        # confirm
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "Load all poses?\n{}".format(input_dna_path),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return None

        # load dna and get poses
        self.dna_obj = dna_viewer.DNA(input_dna_path)
        self.calib_reader = dnacalib.DNACalibDNAReader(self.dna_obj.reader)

        self.attrs = mhBehaviour.get_joint_attrs(self.calib_reader)
        self.attr_defaults = mhBehaviour.get_joint_defaults(self.calib_reader)
        self.poses = mhBehaviour.get_all_poses(self.calib_reader, absolute=False)
        # self.pose_names = mhBehaviour.get_pose_names(self.calib_reader)
        # self.pose_names = [pose.get_display_name() for pose in self.poses]
        # self.set_pose_names(self.pose_names)

        self.model.set_poses(self.poses)

        QtWidgets.QMessageBox.information(
            self,
            "Complete",
            "All poses loaded: {}".format(input_dna_path),
            QtWidgets.QMessageBox.Ok
        )

        return True

    def save(self):
        # check we have an output path
        if not self.path_manager.output_dna_path:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No output DNA path given",
                QtWidgets.QMessageBox.Ok
            )

            return

        # check we have data loaded
        if not self.poses:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No data loaded to save",
                QtWidgets.QMessageBox.Ok
            )

            return

        # confirm
        confirm = QtWidgets.QMessageBox.warning(
            self,
            "confirm",
            "Save all poses?\n{}".format(self.path_manager.output_dna_path),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if confirm is QtWidgets.QMessageBox.Cancel:
            return None

        # write data
        stream = dna.FileStream(
            self.path_manager.output_dna_path, dna.FileStream.AccessMode_Write, dna.FileStream.OpenMode_Binary
        )

        writer = dna.BinaryStreamWriter(stream)
        writer.setFrom(self.calib_reader)

        mhBehaviour.set_all_poses(self.calib_reader, writer, self.poses, from_absolute=False)

        writer.write()

        # confirm write
        if not dna.Status.isOk():
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                status,
                QtWidgets.QMessageBox.Ok
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                "Dna file exported:\n{}".format(self.path_manager.output_dna_path),
                QtWidgets.QMessageBox.Ok
            )

        return True

    def selection_changed(self, old_selection, new_selection):
        pass

    def filter_changed(self):
        self.proxy_model.setFilterWildcard(
            "*{}*".format(self.filter_line_edit.text())
        )

    # def set_pose_names(self, pose_names):
    #     self.model.setStringList(pose_names)
    #     return True

    def get_selected_poses(self, warn=False):
        poses = []

        selection = self.view.selectionModel().selection()

        for proxy_index in selection.indexes():
            index = self.proxy_model.mapToSource(proxy_index)

            pose = self.poses[int(index.row())]

            poses.append(pose)

        if not poses and warn:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No pose selected",
                QtWidgets.QMessageBox.Ok
            )

        return poses

    def reset_scene(self):
        mhJoints.reset_scene_joint_xforms(self.calib_reader)

    def update_scene(self):
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False
        else:
            pose = poses[0]

        pose.pose_joints()

        # mhBehaviour.pose_joints_from_data(
        #     self.calib_reader, self.poses, pose_index,
        #     ignore_namespace=False, defaults=self.attr_defaults
        # )

        return True

    def update_data(self):
        poses = self.get_selected_poses(warn=True)

        if not poses:
            return False
        else:
            pose = poses[0]

        pose.update_from_scene()

        # mhBehaviour.update_pose_data_from_scene(
        #     self.calib_reader, self.poses, pose,
        #     ignore_namespace=False, defaults=self.attr_defaults
        # )

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

        # mhBehaviour.scale_all_poses(
        #     self.poses, scale_value
        # )

        return True


class DnaQCWidget(QtWidgets.QWidget):
    def __init__(self, path_manager, *args, **kwargs):
        super(DnaQCWidget, self).__init__(*args, **kwargs)

        self.dna_obj = None
        self.calib_reader = None

        self.path_manager = path_manager

        self.create_widgets()

    def error(self, err):
        QtWidgets.QMessageBox.critical(
            self,
            "Error",
            str(err),
            QtWidgets.QMessageBox.Ok
        )

    def create_widgets(self):

        # Create tech ROM
        self.tech_rom_box = QtWidgets.QGroupBox("Technical ROM")

        self.dna_combo = QtWidgets.QComboBox()
        self.start_spin = mhWidgets.LabelledSpinBox("Start Frame", default=0, maximum=10000)
        self.frame_interval = mhWidgets.LabelledSpinBox("Frame Interval", default=10, maximum=100)
        self.update_timeline_checkbox = QtWidgets.QCheckBox("Update Timeline")
        self.combos_checkbox = QtWidgets.QCheckBox("Combos")
        self.combine_lr_checkbox = QtWidgets.QCheckBox("Combine LR")
        self.annotate_checkbox = QtWidgets.QCheckBox("Annotate")
        self.namespace_edit = mhWidgets.LabelledLineEdit("Namespace")

        self.update_timeline_checkbox.setChecked(True)
        self.combos_checkbox.setChecked(True)
        self.combine_lr_checkbox.setChecked(True)
        self.annotate_checkbox.setChecked(True)

        self.create_btn = QtWidgets.QPushButton("Create ROM")
        self.create_btn.clicked.connect(self._create_rom_clicked)

        tech_rom_lyt = QtWidgets.QVBoxLayout()
        self.tech_rom_box.setLayout(tech_rom_lyt)

        tech_rom_lyt.addWidget(self.dna_combo)
        tech_rom_lyt.addWidget(self.start_spin)
        tech_rom_lyt.addWidget(self.frame_interval)
        tech_rom_lyt.addWidget(self.update_timeline_checkbox)
        tech_rom_lyt.addWidget(self.combos_checkbox)
        tech_rom_lyt.addWidget(self.combine_lr_checkbox)
        tech_rom_lyt.addWidget(self.annotate_checkbox)
        tech_rom_lyt.addWidget(self.namespace_edit)
        tech_rom_lyt.addWidget(self.create_btn)

        # main layout
        lyt = QtWidgets.QVBoxLayout()
        self.setLayout(lyt)

        lyt.addWidget(self.tech_rom_box)
        lyt.addStretch()

    def update_assets(self):
        self.dna_combo.clear()
        self.dna_combo.addItems(self.path_manager.get_dna_files())
        return True

    def _create_rom_clicked(self):
        try:
            mhSrc.validate_plugin()
        except mhCore.MHError as err:
            self.error(err)
            return False

        namespace = self.namespace_edit.line_edit.text()
        update_timeline = self.update_timeline_checkbox.isChecked()
        annotate = self.annotate_checkbox.isChecked()
        combine_lr = self.combine_lr_checkbox.isChecked()
        combos = self.combos_checkbox.isChecked()
        start_frame = self.start_spin.spin_box.value()
        interval = self.frame_interval.spin_box.value()
        tongue = False
        eyelashes = False

        if combos:
            # get combos from dna file and map to controls
            dna_name = str(self.dna_combo.currentText())
            dna_path = self.path_manager.get_path(dna_name)

            if not os.path.exists(dna_path):
                self.error("Dna path not found: {}".format(dna_path))
                return False

            LOG.info("Loading dna: {}".format(dna_path))
            dna_obj = dna_viewer.DNA(dna_path)
            reader = dnacalib.DNACalibDNAReader(dna_obj.reader)

            poses = mhBehaviour.get_all_poses(reader)
            psd_poses = mhBehaviour.get_psd_poses(reader, poses)

            mapping = mhAnimUtils.map_expressions_to_controls(tongue=tongue, eyelashes=eyelashes, namespace=namespace)

            combo_mapping = mhAnimUtils.map_psds_to_controls(mapping, psd_poses.values())
        else:
            combo_mapping = None

        # animate controls
        if cmds.objExists(mhAnimUtils.ANNOTATION_NAME):
            cmds.delete(mhAnimUtils.ANNOTATION_NAME)

        mhAnimUtils.reset_control_board_anim(namespace=namespace)

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
        )

        return True


class DnaModWidget(
    QtWidgets.QMainWindow
):
    """TODO warning for maya 2023+ about skincluster backward incompatability
    """

    def __init__(self, *args, **kwargs):
        super(DnaModWidget, self).__init__(*args, **kwargs)

        self.path_manager = mhWidgets.DnaPathManager()

        self.setWindowTitle("Bren's MetaHuman DNA Modification Tool")

        self.setCentralWidget(
            QtWidgets.QWidget()
        )

        lyt = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(lyt)

        self.config_group_box = QtWidgets.QGroupBox("config")
        config_lyt = QtWidgets.QVBoxLayout()
        self.config_group_box.setLayout(config_lyt)

        self.dna_assets_dir_widget = mhWidgets.DirWidget("Dna Viewer Dir")
        self.dna_assets_dir_widget.path = mhSrc.get_dna_data_dir()

        self.dna_files_dir_widget = mhWidgets.DirWidget("Dna Files Dir")
        self.dna_files_dir_widget.path = os.path.join(mhSrc.get_dna_data_dir(), "dna_files")

        self.input_file_widget = mhWidgets.PathOpenWidget("Input DNA")
        self.output_file_widget = mhWidgets.PathSaveWidget("Output DNA")

        self.dna_assets_dir_widget.PATH_CHANGED.connect(self.paths_changed)
        self.dna_files_dir_widget.PATH_CHANGED.connect(self.paths_changed)
        self.input_file_widget.PATH_CHANGED.connect(self.paths_changed)
        self.output_file_widget.PATH_CHANGED.connect(self.paths_changed)

        config_lyt.addWidget(self.dna_assets_dir_widget)
        config_lyt.addWidget(self.dna_files_dir_widget)
        config_lyt.addWidget(self.input_file_widget)
        config_lyt.addWidget(self.output_file_widget)

        lyt.addWidget(self.config_group_box)

        self.tabs = QtWidgets.QTabWidget()

        self.build_widget = DnaBuildWidget(self.path_manager)
        self.transfer_widget = DnaTransferWidget(self.path_manager)
        self.poses_widget = DnaPosesWidget(self.path_manager)
        self.qc_widget = DnaQCWidget(self.path_manager)

        self.tabs.addTab(self.build_widget, "build")
        self.tabs.addTab(self.transfer_widget, "transfer")
        self.tabs.addTab(self.poses_widget, "edit poses")
        self.tabs.addTab(self.qc_widget, "QC")

        lyt.addWidget(self.tabs)

        self.paths_changed()

    def paths_changed(self):
        self.path_manager.dna_assets_path = self.dna_assets_dir_widget.path
        self.path_manager.dna_files_path = self.dna_files_dir_widget.path
        self.path_manager.input_dna_path = self.input_file_widget.path
        self.path_manager.output_dna_path = self.output_file_widget.path

        # update widgets
        self.build_widget.update_assets()
        self.transfer_widget.update_assets()
        self.poses_widget.update_assets()
        self.qc_widget.update_assets()

        return True

    @classmethod
    def create(cls, width=500, height=500, show=True):

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
