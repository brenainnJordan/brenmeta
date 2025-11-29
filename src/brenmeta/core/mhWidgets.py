import os

from maya import cmds
from maya import OpenMayaUI
from maya.api import OpenMaya

from Qt import QtCore
from Qt import QtWidgets


class LabelledSpinBox(QtWidgets.QWidget):
    SPIN_BOX_CLS = QtWidgets.QSpinBox

    def __init__(self, name, label_width=80, spin_box_width=80, height=30, default=0, minimum=0, maximum=10, **kwargs):
        super(LabelledSpinBox, self).__init__(**kwargs)

        self.setFixedHeight(height)

        lyt = QtWidgets.QHBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        self.label = QtWidgets.QLabel(name)

        self.spin_box = self.SPIN_BOX_CLS()
        self.spin_box.setValue(default)
        self.spin_box.setMinimum(minimum)
        self.spin_box.setMaximum(maximum)

        self.label.setFixedWidth(label_width)
        self.spin_box.setFixedWidth(spin_box_width)

        lyt.addWidget(self.label)
        lyt.addWidget(self.spin_box)
        lyt.addStretch()


class LabelledDoubleSpinBox(LabelledSpinBox):
    SPIN_BOX_CLS = QtWidgets.QDoubleSpinBox

    def __init__(self, name, label_width=80, spin_box_width=80, height=30, default=0, minimum=0, maximum=10, **kwargs):
        super(LabelledDoubleSpinBox, self).__init__(
            name, label_width=label_width, spin_box_width=spin_box_width, height=height, default=default,
            minimum=minimum, maximum=maximum, **kwargs
        )

class LabelledLineEdit(QtWidgets.QWidget):

    def __init__(self, label, *args, **kwargs):
        super(LabelledLineEdit, self).__init__(*args, **kwargs)

        self.lyt = QtWidgets.QHBoxLayout()
        self.setLayout(self.lyt)

        self.label = QtWidgets.QLabel(label)
        self.label.setFixedWidth(100)
        self.line_edit = QtWidgets.QLineEdit()

        self.lyt.addWidget(self.label)
        self.lyt.addWidget(self.line_edit)

        self.lyt.setContentsMargins(0, 0, 0, 0)
        self.lyt.setSpacing(0)

        # self.line_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.line_edit.setFixedHeight(30)

    @property
    def text(self):
        return self.line_edit.text()

    @text.setter
    def text(self, value):
        self.line_edit.setText(value)


class PathWidgetBase(LabelledLineEdit):
    PATH_CHANGED = QtCore.Signal()

    def __init__(self, label, *args, **kwargs):
        super(PathWidgetBase, self).__init__(label, *args, **kwargs)

        self.caption = label

        self.browse_btn = QtWidgets.QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        # self.browse_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.browse_btn.clicked.connect(self.browse_clicked)

        self.lyt.addWidget(self.browse_btn)

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


class DirWidget(PathWidgetBase):

    def __init__(self, *args, **kwargs):
        super(DirWidget, self).__init__(*args, **kwargs)

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

        return path


class PathOpenWidget(PathWidgetBase):

    def __init__(self, *args, **kwargs):
        super(PathOpenWidget, self).__init__(*args, **kwargs)

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

        return file_path


class PathSaveWidget(PathWidgetBase):

    def __init__(self, *args, **kwargs):
        super(PathSaveWidget, self).__init__(*args, **kwargs)

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

        return file_path


class NodeLineEdit(QtWidgets.QWidget):
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

        # self.line_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # self.set_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

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


class LabelledNamespaceLineEdit(QtWidgets.QWidget):
    def __init__(self, label, *args, **kwargs):
        super(LabelledNamespaceLineEdit, self).__init__(*args, **kwargs)

        self.lyt = QtWidgets.QHBoxLayout()
        self.setLayout(self.lyt)

        self.label = QtWidgets.QLabel(label)
        self.label.setFixedWidth(100)

        self.line_edit = QtWidgets.QLineEdit()

        self.set_btn = QtWidgets.QPushButton("<<")
        self.set_btn.setFixedWidth(30)

        self.lyt.addWidget(self.label)
        self.lyt.addWidget(self.line_edit)
        self.lyt.addWidget(self.set_btn)

        self.lyt.setContentsMargins(0, 0, 0, 0)
        self.lyt.setSpacing(0)

        self.set_btn.clicked.connect(self.set_clicked)

    @property
    def node(self):
        return self.line_edit.text()

    def set_clicked(self):
        self.line_edit.setText("")

        nodes = cmds.ls(sl=True)

        if not nodes:
            return

        if ":" not in nodes[0]:
            return

        self.line_edit.setText(nodes[0].split(":")[0])

        return


class DnaPathManager(object):
    def __init__(self):
        self.input_path = None
        self.output_path = None
        self.dna_assets_path = None
        self.dna_files_path = None

    def get_dna_files(self):
        generic_assets = None

        assets = ["Input Dna", "Output Dna"]

        if self.dna_files_path:
            generic_assets = []

            # dna_path = os.path.join(self.dna_assets_path, "dna_files")

            if os.path.exists(self.dna_files_path):
                for i in os.listdir(self.dna_files_path):
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
                self.dna_files_path,
                "{}.dna".format(asset)
            )

        return dna_path


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
