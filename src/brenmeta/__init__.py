from PySide2 import QtWidgets


def validate_dependencies_v1():
    from brenmeta.core import mhCore
    from brenmeta.dnaMod1 import mhSrc

    try:
        mhSrc.validate_plugin()
        mhSrc.validate_dna_module(force=False)

    except mhCore.MHError as err:
        res = QtWidgets.QMessageBox.question(
            None,
            "Warning",
            "Dependency error: {}\nTry force dependencies?".format(err),
        )

        if res == QtWidgets.QMessageBox.Yes:
            try:
                mhSrc.validate_dna_module(force=True)

            except mhCore.MHError as err:
                QtWidgets.QMessageBox.critical(
                    None,
                    "Error",
                    "Failed to force dependencies: {}".format(err),
                )

    return True

def show(version=1):
    """
    import brenmeta
    gui = brenmeta.show(version=1)
    """

    if version == 1:
        validate_dependencies_v1()

        from brenmeta.dnaMod1 import mhGui

        widget = mhGui.DnaModWidget.create()
        return widget
    else:
        # TODO
        pass
