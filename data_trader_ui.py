import sys

import shiboken2
from PySide2 import QtWidgets, QtCore, QtGui
from maya import OpenMayaUI, cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from . import utility


def delete_window(window):
    if cmds.workspaceControl(window, query=True, exists=True):
        cmds.workspaceControl(window, edit=True, close=True)
        cmds.deleteUI(window, control=True)


def get_maya_window():
    try:
        return shiboken2.wrapInstance(long(OpenMayaUI.MQtUtil.mainWindow()), QtWidgets.QMainWindow)
    except TypeError:
        # Running in console mode
        return None


class DataTraderUI(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=get_maya_window()):
        super(DataTraderUI, self).__init__(parent)

        # Set window parameter
        window_title = "Data Trader"
        self.setWindowTitle(window_title)
        self.setWindowFlags(self.windowFlags() & QtCore.Qt.WindowMinimizeButtonHint)
        self.setMinimumSize(420, 500)

        # Close the window if exist
        if parent:
            delete_window(window_title + "WorkspaceControl")
            self.setObjectName(window_title)

        # Set variables
        self.start_frame = cmds.playbackOptions(query=True, minTime=True)
        self.end_frame = cmds.playbackOptions(query=True, maxTime=True)

        # Build UI
        self.build_ui()

    def closeEvent(self, *args, **kwargs):
        """
            It handles application close when run from terminal
        """
        sys.exit(0)

    def separator(self, title):
        """
            Draw the line to separate element in ui
            :param
                title(str): title of separated block

            :return
                QtWidgets.QHBoxLayout: Return layout with label
        """
        layout = QtWidgets.QHBoxLayout(self)

        label = QtWidgets.QLabel(title)
        label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setLineWidth(5)

        layout.addWidget(label)
        layout.addWidget(line)
        return layout

    def build_ui(self):
        """
            Crete the user interface
        """
        dock = True
        base_layout = QtWidgets.QVBoxLayout(self)

        # Load import ui only when it is launch from maya
        if get_maya_window():
            base_layout.addLayout(self.separator("Import Data"))

            import_layout = QtWidgets.QGridLayout()

            import_btn = QtWidgets.QPushButton("Import")
            import_menu = QtWidgets.QMenu(self)
            import_menu.triggered.connect(self.get_import_action)
            import_menu.addAction("Alembic")
            import_menu.addAction("FBX")
            import_menu.addAction("Obj")
            import_menu.addAction("Pose")
            import_menu.addAction("Shader")
            import_btn.setMenu(import_menu)

            import_layout.addWidget(import_btn, 0, 0)
            base_layout.addLayout(import_layout)

            base_layout.addLayout(self.separator("Export Data"))
        else:
            dock = False

        export_layout = QtWidgets.QGridLayout()

        self.static_export = QtWidgets.QRadioButton("Single frame")
        self.static_export.setChecked(True)
        self.animate_export = QtWidgets.QRadioButton("Animated")

        export_layout.addWidget(self.static_export, 0, 0)
        export_layout.addWidget(self.animate_export, 0, 1)

        self.export_type = QtWidgets.QComboBox()
        self.export_type.addItems(["Alembic", "FBX", "Obj", "Pose", "Shader"])
        self.export_type.currentIndexChanged.connect(self.export_change)

        export_layout.addWidget(self.export_type, 0, 2)

        self.dag_tree = QtWidgets.QTreeWidget()
        self.dag_tree.setHeaderLabel("Outliner")
        self.populate_dag_data()

        export_layout.addWidget(self.dag_tree, 1, 0, 1, 3)

        time_layout = QtWidgets.QHBoxLayout()
        start_label = QtWidgets.QLabel(str(self.start_frame))
        self.frame = QtWidgets.QLineEdit()
        self.frame.setValidator(QtGui.QIntValidator())
        end_label = QtWidgets.QLabel(str(self.end_frame))

        time_layout.addWidget(start_label)
        time_layout.addWidget(self.frame)
        time_layout.addWidget(end_label)

        export_layout.addLayout(time_layout, 2, 0, 1, 2)

        export_btn = QtWidgets.QPushButton("Export Data")
        export_btn.clicked.connect(self.export_data)

        export_layout.addWidget(export_btn, 2, 2)

        base_layout.addLayout(export_layout)

        # Make ui visible
        self.show(dockable=dock)

    def get_import_action(self):
        """
            Get te user option for the import and call the necessary methods
        """
        action = self.sender().sender().text()
        if action == "Alembic" or action == "FBX" or action == "Obj":
            utility.import_file(action)
        elif action == "Pose":
            utility.import_pose()
        elif action == "Shader":
            utility.import_shader()
        else:
            utility.message_box("Something went wrong", QtWidgets.QMessageBox.Warning)

    def populate_dag_data(self):
        """
            Add data into the tree widget
        """
        self.dag_tree.clear()
        exceptional_item = ["persp", "top", "front", "side"]

        for obj in cmds.ls(assemblies=True):
            if obj not in exceptional_item:
                item_level_1 = QtWidgets.QTreeWidgetItem([obj])
                for child in cmds.listRelatives(obj, children=True):
                    item_level_2 = QtWidgets.QTreeWidgetItem([child])
                    item_level_1.addChild(item_level_2)

                self.dag_tree.addTopLevelItem(item_level_1)

    def export_change(self):
        """
            It handles options that are specific to the export type
        """
        current_export_type = self.export_type.currentText()

        if current_export_type == "Shader":
            self.static_export.setEnabled(False)
            self.animate_export.setEnabled(False)
        elif current_export_type == "Obj" or current_export_type == "Pose":
            self.static_export.setChecked(True)
            self.animate_export.setEnabled(False)
        elif current_export_type == "FBX":
            self.animate_export.setChecked(True)
            self.static_export.setEnabled(False)
        else:
            self.static_export.setEnabled(True)
            self.animate_export.setEnabled(True)

    def export_data(self):
        """
            Export selected item from dag_tree
        """
        # Collect required data
        export_type = self.export_type.currentText()

        try:
            obj = self.dag_tree.currentItem().text(0)
        except AttributeError:
            utility.message_box("Selection not found\nPlease select object", QtWidgets.QMessageBox.Warning)
            return

        try:
            frame_number = int(self.frame.text())
        except ValueError:
            if export_type == "Shader" or self.animate_export.isChecked():
                frame_number = None
            else:
                utility.message_box("Frame Number is not valid", QtWidgets.QMessageBox.Critical)
                return

        if self.animate_export.isChecked():
            anim_export = True
        else:
            anim_export = False

        if export_type == "Alembic":
            utility.alembic_export(obj, anim_export, frame_number)
        elif export_type == "FBX":
            utility.fbx_export(obj)
        elif export_type == "Obj":
            utility.obj_export(obj, frame_number)
        elif export_type == "Pose":
            utility.pose_export(obj, frame_number)
        elif export_type == "Shader":
            utility.shader_export(obj)
        else:
            utility.message_box("Export Type is currently not supported", QtWidgets.QMessageBox.Warning)


def show_ui():
    """
        Calls the ui class

        :return
            QtWidgets.QDialog: user interface of the application
    """
    ui = DataTraderUI()
    return ui
