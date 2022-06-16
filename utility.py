import json
import os

from PySide2 import QtWidgets
from maya import cmds, mel


def load_plugin(plugin_name):
    """
        Load the plugin in maya as per the operating system

        :param
            plugin_name(str): Name of the plugin
    """
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def get_filepath(file_type, export, file_mode):
    """
        Open brose dialog to get export path

        :param
            file_type(str): Type of file
            except(bool): whether it is for export or import
            file_mode(QtWidgets.QFileDialog.QFileMode): dialog file mode

        :return
            (str): File path with extension
    """
    file_dialog = QtWidgets.QFileDialog()
    if export:
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
    else:
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)

    if file_type == "Alembic":
        load_plugin("AbcExport")
        load_plugin("AbcImport")
        file_dialog.setNameFilter("Alembic(*.abc)")
        file_dialog.setFileMode(file_mode)

    elif file_type == "FBX":
        load_plugin("fbxmaya")
        file_dialog.setNameFilter("FBX(*.fbx)")
        file_dialog.setFileMode(file_mode)

    elif file_type == "Obj":
        load_plugin("objExport")
        file_dialog.setNameFilter("OBJ(*.obj)")
        file_dialog.setFileMode(file_mode)

    elif file_type == "Pose":
        file_dialog.setNameFilter("Json(*.json")
        file_dialog.setFileMode(file_mode)

    elif file_type == "Shader":
        file_dialog.setFileMode(file_mode)

    else:
        message_box("File type is not supported", QtWidgets.QMessageBox.Warning)

    if file_dialog.exec_():
        return file_dialog.selectedFiles()[0]


"""Export Code Block Start"""


def alembic_export(obj, anim_export, frame_number=None):
    """
        Export alembic data

        :param
            obj(str): Name of object
            anim_export(bool): export animation or static
            frame_number(int): Frame number which data will export
    """
    file_path = get_filepath("Alembic", True, QtWidgets.QFileDialog.AnyFile)
    if anim_export:
        start_frame = cmds.playbackOptions(query=True, minTime=True)
        end_frame = cmds.playbackOptions(query=True, maxTime=True)

        command = 'AbcExport -j "-frameRange {0} {1} -uvWrite -worldSpace -writeVisibility ' \
                  '-dataFormat ogawa -root {2} -file {3}";'.format(start_frame, end_frame, obj, file_path)
    else:
        command = 'AbcExport -j "-frameRange {0} {0} -uvWrite -worldSpace -writeVisibility ' \
                  '-dataFormat ogawa -root {1} -file {2}";'.format(frame_number, obj, file_path)

    mel.eval(command)


def fbx_export(obj):
    """
        Export fbx data

        :param
            obj(str): Name of object
            anim_export(bool): export animation or static
            frame_number(int): Frame number which data will export
    """
    file_path = get_filepath("FBX", True, QtWidgets.QFileDialog.AnyFile)
    cmds.select(obj, replace=True)

    cmds.file(file_path, force=True, type="FBX export", exportSelected=True)


def obj_export(obj, frame_number):
    """
        Export obj data

        :param
            obj(str): Name of object
            frame_number(int): Frame number which data will export
    """
    file_path = get_filepath("Obj", True, QtWidgets.QFileDialog.AnyFile)

    if frame_number:
        cmds.currentTime(frame_number)
    cmds.select(obj, replace=True)

    cmds.file(file_path, force=True, options="groups=1;ptgroups=1;materials=1;smoothing=1;normals=1",
              type="OBJexport", exportSelected=True)


def pose_export(obj, frame_number):
    """
        Export pose data

        :param
            obj(str): Name of object
            frame_number(int): Fame number which data will export
    """
    file_path = get_filepath("Pose", True, QtWidgets.QFileDialog.AnyFile)

    if frame_number:
        cmds.currentTime(frame_number)

    # Hope it is a rig and we get curves
    curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve", fullPath=True)
    transforms = list()

    # Not a rig let's get everything
    if not curves:
        curves = [obj]
        curves += cmds.listRelatives(obj, allDescendents=True, type="transform", fullPath=True)

    for curve in curves:
        transforms.append(cmds.listRelatives(curve, parent=True, fullPath=True)[0])
    # Remove duplicate items
    transforms = list(set(transforms))

    anim_data = {"data_trader": "Pose"}
    for transform in transforms:
        value_data = dict()
        attribute = cmds.listAttr(transform, keyable=True)

        if not attribute:
            continue

        for attr in attribute:
            try:
                value_data[attr] = cmds.getAttr(transform + "." + attr)
            except Exception:
                pass
        anim_data[transform] = value_data

    with open(file_path, "w") as out_file:
        json.dump(anim_data, out_file, indent=4)


def shader_export(obj):
    """
        Export shader data

        :param
            obj(str): Name of object
    """
    file_path = get_filepath("Shader", True, QtWidgets.QFileDialog.Directory)
    # Create folder for the selected object
    # Name should not contain : so replace them with __
    tmp_name = obj.replace(":", "__") if ":" in obj else obj
    file_path = os.path.join(file_path, tmp_name).replace("\\", "/")

    if not os.path.exists(file_path):
        os.makedirs(file_path)

    meshes = cmds.listRelatives(obj, allDescendents=True, type="mesh", fullPath=True)

    shader_data = {"data_trader": "Shader"}
    for mesh in meshes:
        shaders = cmds.listConnections(mesh, type="shadingEngine")

        if not shaders:
            continue
        shaders = list(set(shaders))

        for shader in shaders:
            assign_object = cmds.sets(shader, query=True)
            shader_data[shader] = assign_object

            if shader == "initialShadingGroup":
                continue
            tmp_name = shader.replace(":", "__") if ":" in shader else shader
            shader_path = os.path.join(file_path, tmp_name + ".ma")
            try:
                cmds.select(shader, replace=True, noExpand=True)
                cmds.file(shader_path, force=True, type="mayaAscii", exportSelected=True)
            except Exception:
                pass

    json_file = os.path.join(file_path, "Assign_info.json")
    with open(json_file, "w") as out_file:
        json.dump(shader_data, out_file, indent=4)


"""Export Code Block End"""
"""Import Code Block Start"""


def import_file(import_type):
    """
        Import file like obj, fbx, abc
        :param
            import_type(str): Type of file that is needed
    """
    if import_type == "Alembic":
        file_path = get_filepath("Alembic", False, QtWidgets.QFileDialog.ExistingFile)
        command = 'AbcImport - mode import "{0}";'.format(file_path)
        mel.eval(command)

    elif import_type == "FBX":
        file_path = get_filepath("FBX", False, QtWidgets.QFileDialog.ExistingFile)
        cmds.file(file_path, i=True, type="FBX", mergeNamespacesOnClash=True, namespace=":", options="fbx",
                  importTimeRange="combine")

    elif import_type == "Obj":
        file_path = get_filepath("Obj", False, QtWidgets.QFileDialog.ExistingFile)
        cmds.file(file_path, i=True, type="OBJ", mergeNamespacesOnClash=True, namespace=":", options="mo=1",
                  importTimeRange="combine")


def import_pose():
    """
        Import pose value from file
    """
    file_path = get_filepath("Pose", False, QtWidgets.QFileDialog.ExistingFile)

    with open(file_path, "r") as in_file:
        in_data = json.load(in_file)

    if in_data["data_trader"] != "Pose":
        message_box("This file is not supported", QtWidgets.QMessageBox.Critical)
        return

    for obj in in_data.keys():
        if obj == "data_trader":
            continue

        if cmds.objExists(obj):
            for attr, value in in_data[obj].items():
                try:
                    cmds.setAttr(obj + "." + attr, value)
                except Exception:
                    pass


def shader_assign(obj, shader):
    """
        Assign shader to the object.

        :param
            obj(list): Objects which will get the shader.
            shader(str): Name of the shader
    """
    for item in obj:
        try:
            current_shader = cmds.listConnections(item, type="shadingEngine")

            if current_shader:
                cmds.sets(item, remove=current_shader)

            cmds.sets(item, edit=True, forceElement=shader)
        except Exception:
            pass


def import_shader():
    file_path = get_filepath("Shader", False, QtWidgets.QFileDialog.Directory)
    assign_data = os.path.join(file_path, "Assign_info.json").replace("\\", "/")

    if not os.path.isfile(assign_data):
        message_box("Json file is missing", QtWidgets.QMessageBox.Critical)
        return

    with open(assign_data, "r") as in_file:
        in_data = json.load(in_file)

    if in_data["data_trader"] != "Shader":
        message_box("This file is not supported", QtWidgets.QMessageBox.Critical)
        return

    for shader in in_data.keys():
        if shader == "data_trader":
            continue

        if not cmds.objExists(shader):
            tmp_name = shader.replace(":", "__") if ":" in shader else shader
            shader_path = os.path.join(file_path, tmp_name + ".ma")
            cmds.file(shader_path, i=True, type="mayaAscii", mergeNamespacesOnClash=True, namespace=":")

        shader_assign(in_data[shader], shader)


"""Import Code Block End"""


def message_box(message, icon=QtWidgets.QMessageBox.Information):
    """
        Popup message dialog

        :param
            message(str): Message to be display to user
            icon(QtWidgets.QMessageBox.ICON): Icon to be display with message
    """
    msg_box = QtWidgets.QMessageBox()
    msg_box.setWindowTitle("Data Trader")
    msg_box.setText(message)
    msg_box.setIcon(icon)

    msg_box.exec_()
