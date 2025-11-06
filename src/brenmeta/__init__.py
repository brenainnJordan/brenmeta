from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui

def validate_dependencies():
    from . import mhCore

    try:
        mhCore.validate_plugin()
        mhCore.validate_dna_module(force=False)

    except mhCore.MHError as err:
        res = QtWidgets.QMessageBox.question(
            None,
            "Warning",
            "Dependency error: {}\nTry force dependencies?".format(err),
        )

        if res == QtWidgets.QMessageBox.Yes:
            try:
                mhCore.validate_dna_module(force=True)

            except mhCore.MHError as err:
                QtWidgets.QMessageBox.critical(
                    None,
                    "Error",
                    "Failed to force dependencies: {}".format(err),
                )

    return True

def show():
    """
    import brenmeta
    gui = brenmeta.show()
    """

    validate_dependencies()

    from . import mhGui

    widget = mhGui.DnaSandboxWidget.create()
    return widget
