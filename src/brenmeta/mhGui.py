"""

"""

import os
import shiboken2

from maya import cmds
from maya import OpenMayaUI
from maya.api import OpenMaya

from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui

import dna
import dna_viewer
import dnacalib

from . import mhFaceJoints
from . import mhMesh
from . import mhCore
from . import mhJoints
from . import mhUeUtils
from . import mhBehaviour
from . import mhFaceMaterials
from . import mhFaceMeshes


# GROUP_BOX_STYLE = QtWidgets.QStyleOptionGroupBox()
# GROUP_BOX_STYLE.lineWidth = 2
# GROUP_BOX_STYLE.features = QtWidgets.QStyleOptionFrame.Rounded

class DnaPathWidgetBase(
    QtWidgets.QWidget
):
    PATH_CHANGED = QtCore.Signal()

    def __init__(self, label, *args, **kwargs):
        super(DnaPathWidgetBase, self).__init__(*args, **kwargs)

        self.lyt = QtWidgets.QHBoxLayout()
        self.setLayout(self.lyt)

        self.label = QtWidgets.QLabel(label)
        self.label.setFixedWidth(100)
        self.line_edit = QtWidgets.QLineEdit()
        self.browse_btn = QtWidgets.QPushButton("...")
        self.browse_btn.setFixedWidth(30)

        self.lyt.addWidget(self.label)
        self.lyt.addWidget(self.line_edit)
        self.lyt.addWidget(self.browse_btn)

        self.lyt.setContentsMargins(0, 0, 0, 0)
        self.lyt.setSpacing(0)

        self.line_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.browse_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.browse_btn.clicked.connect(self.browse_clicked)

        self.caption = label
        self.filter = "files (*.dna)"

        self.line_edit.textChanged.connect(self.emit_path_changed)

    @property
    def path(self):
        return self.line_edit.text()

    @path.setter
    def path(self, value):
        self.line_edit.setText(value)

    def browse_clicked(self):
        """Overridible method"""
        return None

    def emit_path_changed(self):
        self.PATH_CHANGED.emit()


class DnaDirWidget(DnaPathWidgetBase):

    def __init__(self, *args, **kwargs):
        super(DnaDirWidget, self).__init__(*args, **kwargs)

    def browse_clicked(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            # "test",
            self.caption,
            self.path,
        )

        if not path:
            return

        self.line_edit.setText(path)

        # self.emit_path_changed()

        return path


class DnaPathOpenWidget(DnaPathWidgetBase):

    def __init__(self, *args, **kwargs):
        super(DnaPathOpenWidget, self).__init__(*args, **kwargs)

    def browse_clicked(self):
        file_path, file_type = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Input Dna file",
            self.path,
            self.filter
        )

        if file_path == "":
            return

        self.line_edit.setText(file_path)

        # self.PATH_CHANGED.emit()

        return file_path


class DnaPathSaveWidget(DnaPathWidgetBase):

    def __init__(self, *args, **kwargs):
        super(DnaPathSaveWidget, self).__init__(*args, **kwargs)

    def browse_clicked(self):
        file_path, file_type = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Output Dna file",
            self.path,
            self.filter
        )

        if file_path == "":
            return

        self.line_edit.setText(file_path)

        # self.PATH_CHANGED.emit()

        return file_path


class NodeLineEdit(
    QtWidgets.QWidget
):

    def __init__(self, default, *args, **kwargs):
        super(NodeLineEdit, self).__init__(*args, **kwargs)

        self.lyt = QtWidgets.QHBoxLayout()
        self.setLayout(self.lyt)

        self.line_edit = QtWidgets.QLineEdit(default)

        self.set_btn = QtWidgets.QPushButton("<<")
        self.set_btn.setFixedWidth(30)

        self.lyt.addWidget(self.line_edit)
        self.lyt.addWidget(self.set_btn)

        self.lyt.setContentsMargins(0, 0, 0, 0)
        self.lyt.setSpacing(0)

        self.line_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.set_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.set_btn.clicked.connect(self.set_clicked)

    @property
    def node(self):
        return self.line_edit.text()

    def set_clicked(self):
        nodes = cmds.ls(sl=True)

        if not nodes:
            self.line_edit.setText("")
        else:
            self.line_edit.setText(nodes[0])

        return True


class DnaPathManager(object):
    def __init__(self):
        self.input_path = None
        self.output_path = None
        self.dna_viewer_data_path = None

    def get_assets(self):
        generic_assets = None

        assets = ["Input Dna", "Output Dna"]

        if self.dna_viewer_data_path:
            generic_assets = []

            dna_path = os.path.join(self.dna_viewer_data_path, "dna_files")

            if os.path.exists(dna_path):
                for i in os.listdir(dna_path):
                    if any([
                        not i.endswith(".dna"),
                    ]):
                        continue

                    generic_assets.append(i.split(".")[0])

        if generic_assets:
            assets += generic_assets

        return assets

    def get_path(self, asset):
        dna_paths = {
            "Input Dna": self.input_dna_path,
            "Output Dna": self.output_dna_path,
        }

        if asset in dna_paths:
            dna_path = dna_paths[asset]

        else:
            dna_path = os.path.join(
                self.dna_viewer_data_path,
                "dna_files",
                "{}.dna".format(asset)
            )

        return dna_path


# class DnaAssetCombo(QtWidgets.QComboBox):
#     def __init__(self, *args, **kwargs):
#         super(DnaAssetCombo, self).__init__(*args, **kwargs)
#
#     def update_assets(self, dna_viewer_data_path):
#         self.clear()
#
#         generic_assets = None
#
#         assets = ["Input Dna", "Output Dna"]
#
#         if dna_viewer_data_path:
#             generic_assets = []
#
#             dna_path = os.path.join(dna_viewer_data_path, "dna_files")
#
#             if os.path.exists(dna_path):
#                 for i in os.listdir(dna_path):
#                     if any([
#                         not i.endswith(".dna"),
#                     ]):
#                         continue
#
#                     generic_assets.append(i.split(".")[0])
#
#         if generic_assets:
#             assets += generic_assets
#
#         self.addItems(assets)
#
#         return True


class DnaTransferMeshWidget(QtWidgets.QWidget):
    def __init__(self, label, src, dst, *args, **kwargs):
        super(DnaTransferMeshWidget, self).__init__(*args, **kwargs)

        self.setFixedHeight(30)

        lyt = QtWidgets.QHBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        self.checkbox = QtWidgets.QCheckBox(label)
        self.checkbox.setCheckState(QtCore.Qt.Checked)
        self.checkbox.setFixedWidth(80)

        self.src = NodeLineEdit(src)
        self.dst = NodeLineEdit(dst)

        lyt.addWidget(self.checkbox)
        lyt.addWidget(self.src)
        lyt.addWidget(self.dst)


class DnaTransferWidget(QtWidgets.QWidget):

    def __init__(self, path_manager, *args, **kwargs):
        super(DnaTransferWidget, self).__init__(*args, **kwargs)

        # self.input_dna_path = None
        # self.output_dna_path = None
        # self.dna_viewer_data_path = None

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
        self.inner_mouth_checkbox = QtWidgets.QCheckBox("inner mouth")
        self.cleanup_checkbox = QtWidgets.QCheckBox("cleanup")

        for checkbox in [
            self.eyeballs_checkbox,
            self.eyelashes_checkbox,
            self.eyewet_checkbox,
            self.inner_mouth_checkbox,
            self.cleanup_checkbox,
        ]:
            checkbox.setCheckState(QtCore.Qt.Checked)
            checkbox.setFixedWidth(80)
            meshes_lyt.addWidget(checkbox)

        self.transfer_face_meshes_btn = QtWidgets.QPushButton("transfer face meshes")
        self.transfer_face_meshes_btn.clicked.connect(self.transfer_face_meshes)

        meshes_lyt.addWidget(self.transfer_face_meshes_btn)

        # transfer joints
        self.transfer_joints_group_box = QtWidgets.QGroupBox("transfer joints")

        joints_lyt = QtWidgets.QVBoxLayout()
        self.transfer_joints_group_box.setLayout(joints_lyt)

        self.head = DnaTransferMeshWidget("Head", "src_head_lod0_mesh", "head_lod0_mesh")
        self.teeth = DnaTransferMeshWidget("Teeth", "src_teeth_lod0_mesh", "teeth_lod0_mesh")
        self.left_eye = DnaTransferMeshWidget("Left Eye", "src_eyeLeft_lod0_mesh", "eyeLeft_lod0_mesh")
        self.right_eye = DnaTransferMeshWidget("Right Eye", "src_eyeRight_lod0_mesh", "eyeRight_lod0_mesh")

        self.neck_checkbox = QtWidgets.QCheckBox("Move neck")
        self.neck_checkbox.setCheckState(QtCore.Qt.Checked)

        self.freeze_checkbox = QtWidgets.QCheckBox("Freeze transforms")
        self.freeze_checkbox.setCheckState(QtCore.Qt.Checked)

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

        self.update_mesh_checkbox = QtWidgets.QCheckBox("update meshes")
        self.update_mesh_checkbox.setChecked(QtCore.Qt.Checked)

        self.update_joints_checkbox = QtWidgets.QCheckBox("update joints")
        self.update_joints_checkbox.setChecked(QtCore.Qt.Checked)

        self.calculate_lods_checkbox = QtWidgets.QCheckBox("calculate lods")
        self.calculate_lods_checkbox.setChecked(QtCore.Qt.Checked)

        self.update_btn = QtWidgets.QPushButton("Update")
        self.update_btn.clicked.connect(self.update_dna)

        update_dna_lyt.addWidget(self.input_dna_combo)
        update_dna_lyt.addWidget(self.update_mesh_checkbox)
        update_dna_lyt.addWidget(self.update_joints_checkbox)
        update_dna_lyt.addWidget(self.calculate_lods_checkbox)
        update_dna_lyt.addWidget(self.update_btn)

        # main lyt
        lyt.addWidget(self.transfer_meshes_group_box)
        lyt.addWidget(self.transfer_joints_group_box)
        lyt.addWidget(self.update_dna_group_box)
        lyt.addStretch()

    def update_assets(self):
        self.input_dna_combo.clear()
        self.input_dna_combo.addItems(self.path_manager.get_assets())
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
        if not any([
            self.update_mesh_checkbox.isChecked(),
            self.update_joints_checkbox.isChecked(),
            self.calculate_lods_checkbox.isChecked(),
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

        # dna_paths = {
        #     "Input Dna": self.input_dna_path,
        #     "Output Dna": self.output_dna_path,
        # }
        #
        # input_dna_path = dna_paths[input_dna]
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

        if self.update_joints_checkbox.isChecked():
            mhJoints.update_joint_neutral_xforms(calib_reader)

        if self.update_mesh_checkbox.isChecked():
            mhMesh.update_meshes_from_scene(dna_obj, calib_reader)

        if self.calculate_lods_checkbox.isChecked():
            mhMesh.calculate_lods(dna_obj, calib_reader)

        mhCore.save_dna(calib_reader, self.path_manager.output_dna_path, validate=False)

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


class RepathWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(RepathWidget, self).__init__(*args, **kwargs)

        lyt = QtWidgets.QHBoxLayout()

        self.search_label = QtWidgets.QLabel("search:")
        self.search_label.setFixedWidth(40)

        self.search_line_edit = QtWidgets.QLineEdit()

        self.replace_label = QtWidgets.QLabel("replace:")
        self.replace_label.setFixedWidth(40)

        self.replace_line_edit = QtWidgets.QLineEdit()

        self.repath_btn = QtWidgets.QPushButton("repath")
        self.repath_btn.clicked.connect(self.repath)

        lyt.addWidget(self.search_label)
        lyt.addWidget(self.search_line_edit)
        lyt.addWidget(self.replace_label)
        lyt.addWidget(self.replace_line_edit)
        lyt.addWidget(self.repath_btn)

        self.setLayout(lyt)

    def repath(self):
        attrs = cmds.filePathEditor(query=True, listFiles="", attributeOnly=True)

        cmds.filePathEditor(
            attrs,
            replaceString=[self.search_line_edit.text(), self.replace_line_edit.text()],
            replaceAll=True
        )

        return True


class DnaBuildWidget(QtWidgets.QWidget):

    def __init__(self, path_manager, *args, **kwargs):
        super(DnaBuildWidget, self).__init__(*args, **kwargs)

        # self.input_dna_path = None
        # self.output_dna_path = None
        # self.dna_viewer_data_path = dna_viewer_data_path
        self.path_manager = path_manager

        lyt = QtWidgets.QVBoxLayout()
        self.setLayout(lyt)

        # build
        self.build_group_box = QtWidgets.QGroupBox("build rig")

        build_lyt = QtWidgets.QVBoxLayout()
        self.build_group_box.setLayout(build_lyt)

        self.build_combo = QtWidgets.QComboBox()

        self.full_rig_checkbox = QtWidgets.QCheckBox("full rig")

        self.build_btn = QtWidgets.QPushButton("Build")
        self.build_btn.setFixedHeight(30)
        self.build_btn.clicked.connect(self.build_rig)

        build_lyt.addWidget(self.build_combo)
        build_lyt.addWidget(self.full_rig_checkbox)
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

        self.repath_widget = RepathWidget()

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
        self.build_combo.addItems(self.path_manager.get_assets())
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

    def build_rig(self):

        build_mode = str(self.build_combo.currentText())

        dna_path = self.path_manager.get_path(build_mode)

        # dna_paths = {
        #     "Input Dna": self.input_dna_path,
        #     "Output Dna": self.output_dna_path,
        # }
        #
        # if build_mode in dna_paths:
        #     dna_path = dna_paths[build_mode]
        #
        # else:
        #     dna_path = os.path.join(
        #         self.dna_viewer_data_path,
        #         "dna_files",
        #         "{}.dna".format(build_mode)
        #     )

        if not os.path.exists(dna_path):
            self.error("Dna path not found: {}".format(dna_path))
            return False

        analog_gui = os.path.join(self.path_manager.dna_viewer_data_path, "analog_gui.ma")

        gui = os.path.join(self.path_manager.dna_viewer_data_path, "gui.ma")

        additional_assemble_script = os.path.join(
            self.path_manager.dna_viewer_data_path, "additional_assemble_script.py"
        )

        full_rig = self.full_rig_checkbox.isChecked()

        dna = dna_viewer.DNA(dna_path)

        if full_rig:
            config = dna_viewer.RigConfig(
                gui_path=gui,
                analog_gui_path=analog_gui,
                aas_path=additional_assemble_script,
            )

            dna_viewer.build_rig(dna=dna, config=config)
        else:
            config = dna_viewer.Config(
                add_joints=True,
                add_blend_shapes=False,
                add_skin_cluster=False,
                lod_filter=[0],
            )

            dna_viewer.build_meshes(dna=dna, config=config)

        return True


class DnaPosesWidget(QtWidgets.QWidget):
    def __init__(self, path_manager, *args, **kwargs):
        super(DnaPosesWidget, self).__init__(*args, **kwargs)

        self.dna_obj = None
        self.calib_reader = None
        self.poses_data = None

        # self.input_dna_path = None
        # self.output_dna_path = None
        # self.dna_viewer_data_path = None
        self.path_manager = path_manager

        self.input_combo = QtWidgets.QComboBox()

        self.load_btn = QtWidgets.QPushButton("load poses")
        self.save_btn = QtWidgets.QPushButton("save output dna")

        self.load_btn.clicked.connect(self.load)
        self.save_btn.clicked.connect(self.save)

        self.path_line_edit = QtWidgets.QLineEdit()

        self.model = QtCore.QStringListModel()
        self.proxy_model = QtCore.QSortFilterProxyModel()

        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self.view = QtWidgets.QListView()
        self.view.setModel(self.proxy_model)
        self.view.setSelectionMode(self.view.SelectionMode.ExtendedSelection)

        self.get_pose_btn = QtWidgets.QPushButton("get")
        self.set_pose_btn = QtWidgets.QPushButton("set")
        self.mirror_pose_btn = QtWidgets.QPushButton("mirror")
        self.reset_pose_btn = QtWidgets.QPushButton("reset")

        self.get_pose_btn.clicked.connect(self.get_pose)
        self.set_pose_btn.clicked.connect(self.set_pose)
        self.mirror_pose_btn.clicked.connect(self.mirror_pose)
        self.reset_pose_btn.clicked.connect(self.reset_pose)

        self.input_lyt = QtWidgets.QHBoxLayout()
        self.input_lyt.addWidget(self.input_combo)
        self.input_lyt.addWidget(self.load_btn)

        self.view_btn_lyt = QtWidgets.QVBoxLayout()

        self.view_btn_lyt.addWidget(self.get_pose_btn)
        self.view_btn_lyt.addWidget(self.set_pose_btn)
        self.view_btn_lyt.addWidget(self.mirror_pose_btn)
        self.view_btn_lyt.addWidget(self.reset_pose_btn)
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

        QtCore.QObject.connect(
            self.view.selectionModel(),
            QtCore.SIGNAL("currentChanged(QModelIndex, QModelIndex)"),
            self.selection_changed
        )

        QtCore.QObject.connect(
            self.view.selectionModel(),
            QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.selection_changed
        )

    def update_assets(self):
        self.input_combo.clear()
        self.input_combo.addItems(self.path_manager.get_assets())
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

        self.poses_data = mhBehaviour.get_all_poses(self.calib_reader)

        self.set_poses(self.calib_reader, self.poses_data)

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
        if not self.poses_data:
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

        mhBehaviour.set_all_poses(self.calib_reader, writer, self.poses_data, from_absolute=True)

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
        self.proxy_model.setFilterWildcard(self.filter_line_edit.text())

    def set_poses(self, reader, data):
        pose_names = []

        for i, pose_data in enumerate(data):
            raw_control = reader.getRawControlName(i)

            if raw_control:
                pose_names.append(raw_control)
            else:
                pose_names.append(str(i))

        self.model.setStringList(pose_names)

        return True

    def get_selected_poses(self):
        poses = []

        selection = self.view.selectionModel().selection()

        for proxy_index in selection.indexes():
            index = self.proxy_model.mapToSource(proxy_index)
            pose = str(index.data())
            poses.append(pose)

        return poses

    def reset_pose(self):
        mhJoints.reset_scene_joint_xforms(self.calib_reader)

    def get_pose(self):
        poses = self.get_selected_poses()

        if not poses:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No pose selected",
                QtWidgets.QMessageBox.Ok
            )

            return False
        else:
            pose = poses[0]

        mhBehaviour.pose_joints_from_data(
            self.calib_reader, self.poses_data, pose, ignore_namespace=False
        )

        return True

    def set_pose(self):
        poses = self.get_selected_poses()

        if not poses:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "No pose selected",
                QtWidgets.QMessageBox.Ok
            )

            return False
        else:
            pose = poses[0]

        mhBehaviour.update_pose_data_from_scene(
            self.calib_reader, self.poses_data, pose, ignore_namespace=False
        )

        return True

    def mirror_pose(self):
        QtWidgets.QMessageBox.warning(
            self,
            "Warning",
            "Mirror pose not yet implemented",
            QtWidgets.QMessageBox.Ok
        )


class DnaSandboxWidget(
    QtWidgets.QMainWindow
):

    def __init__(self, *args, **kwargs):
        super(DnaSandboxWidget, self).__init__(*args, **kwargs)

        self.path_manager = DnaPathManager()

        self.setWindowTitle("Bren's MetaHuman DNA sandbox")

        self.setCentralWidget(
            QtWidgets.QWidget()
        )

        lyt = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(lyt)

        self.config_group_box = QtWidgets.QGroupBox("config")
        config_lyt = QtWidgets.QVBoxLayout()
        self.config_group_box.setLayout(config_lyt)

        self.dna_viewer_dir_widget = DnaDirWidget("Dna Viewer Dir")
        self.dna_viewer_dir_widget.path = mhCore.DNA_DATA_DIR
        self.dna_viewer_dir_widget.setFixedHeight(30)

        self.input_file_widget = DnaPathOpenWidget("Input DNA")
        self.output_file_widget = DnaPathSaveWidget("Output DNA")

        self.input_file_widget.setFixedHeight(30)
        self.output_file_widget.setFixedHeight(30)

        self.dna_viewer_dir_widget.PATH_CHANGED.connect(self.paths_changed)
        self.input_file_widget.PATH_CHANGED.connect(self.paths_changed)
        self.output_file_widget.PATH_CHANGED.connect(self.paths_changed)

        config_lyt.addWidget(self.dna_viewer_dir_widget)
        config_lyt.addWidget(self.input_file_widget)
        config_lyt.addWidget(self.output_file_widget)

        lyt.addWidget(self.config_group_box)

        self.tabs = QtWidgets.QTabWidget()

        self.build_widget = DnaBuildWidget(self.path_manager)
        self.transfer_widget = DnaTransferWidget(self.path_manager)
        self.poses_widget = DnaPosesWidget(self.path_manager)

        self.tabs.addTab(self.build_widget, "build")
        self.tabs.addTab(self.transfer_widget, "transfer")
        self.tabs.addTab(self.poses_widget, "edit poses")

        lyt.addWidget(self.tabs)

        self.paths_changed()

    def paths_changed(self):
        self.path_manager.dna_viewer_data_path = self.dna_viewer_dir_widget.path
        self.path_manager.input_dna_path = self.input_file_widget.path
        self.path_manager.output_dna_path = self.output_file_widget.path

        # self.build_widget.dna_viewer_data_path = self.dna_viewer_dir_widget.path
        # self.build_widget.input_dna_path = self.input_file_widget.path
        # self.build_widget.output_dna_path = self.output_file_widget.path
        #
        # self.transfer_widget.dna_viewer_data_path = self.dna_viewer_dir_widget.path
        # self.transfer_widget.input_dna_path = self.input_file_widget.path
        # self.transfer_widget.output_dna_path = self.output_file_widget.path
        #
        # self.poses_widget.dna_viewer_data_path = self.dna_viewer_dir_widget.path
        # self.poses_widget.input_dna_path = self.input_file_widget.path
        # self.poses_widget.output_dna_path = self.output_file_widget.path

        # update widgets
        self.build_widget.update_assets()
        self.transfer_widget.update_assets()
        self.poses_widget.update_assets()

        return True

    @classmethod
    def create(cls, width=500, height=500, show=True):

        maya_main_window_ptr = OpenMayaUI.MQtUtil.mainWindow()
        maya_main_window = shiboken2.wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)

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
