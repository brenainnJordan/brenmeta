from . import mhGui

def show():
    """
    import brenmeta
    gui = brenmeta.show()
    """
    widget = mhGui.DnaSandboxWidget.create()
    return widget
