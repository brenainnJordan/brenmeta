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

"""General reusable widgets"""

import json

from maya import cmds
from maya import OpenMayaUI
from maya.api import OpenMaya

from Qt import QtCore
from Qt import QtWidgets
from Qt import QtGui

from brenmeta.core import mhCore


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

    def __init__(self, label, default=None, parent=None):
        super(LabelledLineEdit, self).__init__(parent=parent)

        self.lyt = QtWidgets.QHBoxLayout()
        self.setLayout(self.lyt)

        self.label = QtWidgets.QLabel(label)
        self.label.setFixedWidth(100)

        self.line_edit = QtWidgets.QLineEdit()

        if default:
            self.line_edit.setText(default)

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

        self.filter = "files (*.*)"

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
            self.caption,
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
            self.caption,
            self.path,
            self.filter
        )

        if file_path == "":
            return

        self.line_edit.setText(file_path)

        return file_path


class NodeLineEdit(QtWidgets.QWidget):
    def __init__(self, default=None, label=None, label_width=None, parent=None):
        super(NodeLineEdit, self).__init__(parent=parent)

        self.lyt = QtWidgets.QHBoxLayout()
        self.setLayout(self.lyt)

        self.line_edit = QtWidgets.QLineEdit()

        if default:
            self.line_edit.setText(default)

        self.set_btn = QtWidgets.QPushButton("<<")
        self.set_btn.setFixedWidth(30)

        if label:
            self.label = QtWidgets.QLabel(label)

            if label_width is not None:
                self.label.setFixedWidth(label_width)

            self.lyt.addWidget(self.label)
        else:
            self.label = None

        self.lyt.addWidget(self.line_edit)
        self.lyt.addWidget(self.set_btn)

        self.lyt.setContentsMargins(0, 0, 0, 0)
        self.lyt.setSpacing(0)

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


class DnaPathManagerWidget(QtWidgets.QGroupBox):
    def __init__(self, path_manager, name, parent=None):
        super(DnaPathManagerWidget, self).__init__(name, parent=parent)
        self.path_manager = path_manager

        self.combo = QtWidgets.QComboBox()
        self.file_edit = None

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.combo)

        self.update_assets()
        self.combo.currentIndexChanged.connect(self._combo_changed)

    def _combo_changed(self):
        if self.combo.currentText() == "other" and self.layout().count() == 1:
            self.file_edit = PathOpenWidget("dna file")
            self.layout().addWidget(self.file_edit)
        elif self.layout().count() == 2:
            self.layout().removeWidget(self.file_edit)
            self.file_edit = None

    def update_assets(self):
        self.combo.clear()
        self.combo.addItems(self.path_manager.get_dna_files())
        self.combo.addItem("other")
        return True

    def get_path(self):
        if self.combo.currentText() == "other":
            return self.file_edit.path
        else:
            return self.path_manager.get_path(self.combo.currentText())


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

        self.src = NodeLineEdit(default=src)
        self.dst = NodeLineEdit(default=dst)

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


class ListModel(QtCore.QAbstractTableModel):
    """
    A Qt model that exposes a list as an editable table.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = None
        self._list_type = None

    @property
    def list(self):
        return self._list

    def set_list(self, list_data):
        self.beginResetModel()
        # Infer type from first items
        self._list_type = type(list_data[0])
        self._list = list_data
        self.endResetModel()

    @property
    def list_type(self):
        return self._list_type

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.list)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not self.list:
            return None

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return self.list[index.row()]

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole or not index.isValid() or not self.list:
            return False

        # type coercion
        try:
            value = self.list_type(value)
        except Exception:
            pass

        self.list[index.row()] = value

        self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
        return True

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.list:
            return False

        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for _ in range(count):
            self.list.insert(row, self.list_type())
        self.endInsertRows()

        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.list:
            return False

        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        for _ in range(count):
            del self.list[row]
        self.endRemoveRows()
        return True


class TupleListModel(QtCore.QAbstractTableModel):
    """
    A Qt model that exposes a list of tuples as an editable table.
    Each tuple becomes a row; each tuple element becomes a column.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tuple_list = None
        self._headers = None
        self._column_types = None
        self._column_count = 0

    @property
    def tuple_list(self):
        return self._tuple_list

    def set_tuple_list(self, tuple_list):
        self.beginResetModel()
        # Infer column count and type from first tuple
        self._column_count = len(tuple_list[0]) if tuple_list else 0
        self._column_types = [type(i) for i in tuple_list[0]]
        self._tuple_list = tuple_list
        self.endResetModel()

    @property
    def column_types(self):
        return self._column_types

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, value):
        mhCore.validate_arg("headers", value, list)
        self.beginResetModel()
        self._headers = value
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.tuple_list)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return self._column_count

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not self.tuple_list:
            return None

        row, col = index.row(), index.column()
        value = self.tuple_list[row][col]

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return value

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole or not index.isValid() or not self.tuple_list:
            return False

        row, column = index.row(), index.column()
        old_tuple = self.tuple_list[row]

        # type coercion
        try:
            value = self.column_types[column](value)
        except Exception:
            pass

        # Rebuild tuple (since tuples are immutable)
        new_tuple = list(old_tuple)
        new_tuple[column] = value
        self.tuple_list[row] = tuple(new_tuple)

        self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
        return True

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.tuple_list:
            return False

        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for _ in range(count):
            self.tuple_list.insert(row, tuple(column_type() for column_type in self.column_types))
        self.endInsertRows()

        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.tuple_list:
            return False

        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        for _ in range(count):
            del self.tuple_list[row]
        self.endRemoveRows()
        return True

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Horizontal:
            if self.headers:
                if section < len(self.headers):
                    return self.headers[section]

            return f"Col {section}"
        else:
            return f"{section}"


class ProjectListModel(QtCore.QAbstractListModel):
    """
    A Qt model that exposes a list as an editable table.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project = None
        self._project_attr = None

    @property
    def project(self):
        return self._project

    @property
    def project_attr(self):
        return self._project_attr

    @property
    def list(self):
        if not self.project or not self.project_attr:
            return None

        if not hasattr(self.project, self.project_attr):
            return None

        return getattr(self.project, self.project_attr)

    def set_project(self, project, project_attr):
        self.beginResetModel()
        self._project = project
        self._project_attr = project_attr
        self.endResetModel()

    # @property
    # def list_type(self):
    #     return self._list_type

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not self.list:
            return 0

        return len(self.list)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not self.list:
            return None

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return self.list[index.row()]

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole or not index.isValid() or not self.list:
            return False

        # # type coercion
        # try:
        #     value = self.list_type(value)
        # except Exception:
        #     pass

        self.list[index.row()] = value

        self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])

        return True

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.list:
            return False

        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for _ in range(count):
            self.list.insert(row, None)
        self.endInsertRows()

        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.list:
            return False

        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        for _ in range(count):
            del self.list[row]
        self.endRemoveRows()
        return True


class ProjectTableModel(QtCore.QAbstractTableModel):
    """
    A Qt model that exposes a list of tuples as an editable table.
    Each tuple becomes a row; each tuple element becomes a column.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # self._tuple_list = None
        self._headers = None
        # self._column_types = None
        # self._column_count = 0

        self._project = None
        self._project_attr = None

    @property
    def project(self):
        return self._project

    @property
    def project_attr(self):
        return self._project_attr

    @property
    def table(self):
        if not self.project or not self.project_attr:
            return None

        if not hasattr(self.project, self.project_attr):
            return None

        return getattr(self.project, self.project_attr)

    def set_project(self, project, project_attr):
        self.beginResetModel()
        self._project = project
        self._project_attr = project_attr
        self.endResetModel()

    # @property
    # def tuple_list(self):
    #     return self._tuple_list
    #
    # def set_tuple_list(self, tuple_list):
    #     self.beginResetModel()
    #     # Infer column count and type from first tuple
    #     self._column_count = len(tuple_list[0]) if tuple_list else 0
    #     self._column_types = [type(i) for i in tuple_list[0]]
    #     self._tuple_list = tuple_list
    #     self.endResetModel()

    # @property
    # def column_types(self):
    #     return self._column_types

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, value):
        mhCore.validate_arg("headers", value, list)
        self.beginResetModel()
        self._headers = value
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not self.table:
            return 0

        return len(self.table)

    def columnCount(self, parent=QtCore.QModelIndex()):
        if not self.table:
            return 0

        # Infer column count and type from first tuple
        column_count = len(self.table[0])

        return column_count

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not self.table:
            return None

        row, col = index.row(), index.column()
        value = self.table[row][col]

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return value

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole or not index.isValid() or not self.table:
            return False

        row, column = index.row(), index.column()
        old_tuple = self.table[row]

        # # type coercion
        # try:
        #     value = self.column_types[column](value)
        # except Exception:
        #     pass

        # # Rebuild tuple (since tuples are immutable)
        # new_tuple = list(old_tuple)
        # new_tuple[column] = value
        self.table[row][column] = value

        self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
        return True

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.table:
            return False

        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)

        for _ in range(count):
            # self.table.insert(row, [column_type() for column_type in self.column_types])
            self.table.insert(row, [None] * self.columnCount())

        self.endInsertRows()

        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        if not self.tuple_list:
            return False

        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)

        for _ in range(count):
            del self.table[row]

        self.endRemoveRows()

        return True

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Horizontal:
            if self.headers:
                if section < len(self.headers):
                    return self.headers[section]

        return str(section)


class TableGroup(QtWidgets.QGroupBox):
    # TODO import/export data
    def __init__(self, parent=None):
        super(TableGroup, self).__init__(parent)

        self.view = QtWidgets.QTableView()

        self.add_btn = QtWidgets.QPushButton("+")
        self.add_btn.clicked.connect(self._add_clicked)

        self.rem_btn = QtWidgets.QPushButton("-")
        self.rem_btn.clicked.connect(self._rem_clicked)

        self.btn_lyt = QtWidgets.QHBoxLayout()
        self.btn_lyt.addWidget(self.add_btn)
        self.btn_lyt.addWidget(self.rem_btn)
        self.btn_lyt.addStretch()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.view)
        self.layout().addLayout(self.btn_lyt)

    def _add_clicked(self):
        if not self.view.model():
            return

        self.view.model().insertRows(self.view.model().rowCount(), 1)

    def _rem_clicked(self):
        if not self.view.model():
            return

        self.view.model().removeRows(self.view.currentIndex().row(), 1)


class JsonHighlighter(QtGui.QSyntaxHighlighter):
    """copilot code TODO test!
    """

    def __init__(self, parent=None):
        super(JsonHighlighter, self).__init__(parent)

        def fmt(color, bold=False):
            f = QtGui.QTextCharFormat()
            f.setForeground(QtGui.QColor(color))
            if bold:
                f.setFontWeight(QtGui.QFont.Bold)
            return f

        self.rules = []

        # Keys
        self.rules.append((
            QtCore.QRegularExpression(r'"([^"\\]|\\.)*"\s*(?=:)'),
            fmt("#7aa2f7", True)
        ))

        # Strings
        self.rules.append((
            QtCore.QRegularExpression(r'\"([^\"\\]|\\.)*\"'),
            fmt("#9ece6a")
        ))

        # Numbers
        self.rules.append((
            QtCore.QRegularExpression(r'\b-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?\b'),
            fmt("#e0af68")
        ))

        # Booleans & null
        self.rules.append((
            QtCore.QRegularExpression(r'\b(true|false|null)\b'),
            fmt("#bb9af7", True)
        ))

        # Braces / brackets
        self.rules.append((
            QtCore.QRegularExpression(r'[{}\[\]]'),
            fmt("#c0caf5", True)
        ))

    def highlightBlock(self, text):
        for pattern, format in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), format)


class JsonEditorDialog(QtWidgets.QDialog):
    """copilot code TODO test!
    """

    def __init__(self, parent=None):
        super(JsonEditorDialog, self).__init__(parent)

        self.setWindowTitle("Edit JSON")
        self.resize(600, 500)

        layout = QtWidgets.QVBoxLayout(self)

        # Editor
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setFont(QtGui.QFont("Consolas", 11))
        self.editor.textChanged.connect(self.validate_json)

        self.highlighter = JsonHighlighter(self.editor.document())

        # Error label
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #f7768e;")
        self.error_label.setVisible(False)

        # Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept_if_valid)
        btns.rejected.connect(self.reject)

        layout.addWidget(self.editor)
        layout.addWidget(self.error_label)
        layout.addWidget(btns)

    # --- API -------------------------------------------------------------

    def load_json(self, data):
        self.editor.setPlainText(json.dumps(data, indent=4))

    def get_json(self):
        return json.loads(self.editor.toPlainText())

    # --- Validation ------------------------------------------------------

    def validate_json(self):
        text = self.editor.toPlainText()
        try:
            json.loads(text)
            self.error_label.setVisible(False)
            return True
        except Exception as e:
            self.error_label.setText(str(e))
            self.error_label.setVisible(True)
            return False

    def accept_if_valid(self):
        if self.validate_json():
            self.accept()
        else:
            # Keep dialog open, highlight error
            QtWidgets.QApplication.beep()
