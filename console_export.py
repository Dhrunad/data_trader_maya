"""
    This file export data in console mode
"""
import sys

from PySide2 import QtWidgets
from maya import standalone, cmds


def get_maya_file():
    """
        Open file browser dialog to get maya file

        :return
            (str): maya file path
    """
    file_dialog = QtWidgets.QFileDialog()
    file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    file_dialog.setNameFilters(["Maya ASCII(*.ma)", "Maya Binary(*.mb)"])

    if file_dialog.exec_():
        maya_file = file_dialog.selectedFiles()[0]
        if maya_file.endswith(".ma") or maya_file.endswith(".mb"):
            return maya_file

    return None


if __name__ == "__main__":
    # Create Qt Application for dialogs
    app = QtWidgets.QApplication(sys.argv)

    # Get maya file
    file_path = get_maya_file()
    if not file_path:
        print "Maya file not found"
        sys.exit(0)

    # Open Maya file
    standalone.initialize()
    cmds.file(file_path, o=True, force=True)

    # Load script for export data
    script_path = "D:/maya_tools"

    if script_path not in sys.path:
        sys.path.append(script_path)

    from data_trader import data_trader_ui
    ui = data_trader_ui.show_ui()

    sys.exit(app.exec_())
