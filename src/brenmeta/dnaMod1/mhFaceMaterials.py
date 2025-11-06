import os
from maya import cmds

from brenmeta.core import mhCore

MATERIAL_MAPPING = {
    "shader_body_shader": None,
    "shader_eyeEdge_shader": ["eyeEdge", "cartilage"],
    "shader_eyeLeft_shader": ["eyeLeft"],
    "shader_eyeRight_shader": ["eyeRight"],
    "shader_eyelashesShadow_shader": None,
    "shader_eyelashes_shader": ["eyelashes"],
    "shader_eyeshell_shader": ["eyeshell"],
    "shader_head_shader": ["head"],
    "shader_saliva_shader": ["saliva"],
    "shader_teeth_shader": ["teeth"],
}

MATERIAL_CHANNEL_MAPPING = {
    "head_cm2_color_head_wm2_browsDown_L": "maskWeight_00",
    "head_cm2_color_head_wm2_browsDown_R": "maskWeight_02",
    "head_cm2_color_head_wm2_browsLateral_L": "maskWeight_04",
    "head_cm2_color_head_wm2_browsLateral_R": "maskWeight_06",
    "head_cm1_color_head_wm1_browsRaiseInner_L": "maskWeight_08",
    "head_cm1_color_head_wm1_browsRaiseInner_R": "maskWeight_10",
    "head_cm1_color_head_wm1_browsRaiseOuter_L": "maskWeight_12",
    "head_cm1_color_head_wm1_browsRaiseOuter_R": "maskWeight_14",
    "head_cm1_color_head_wm1_blink_L": "maskWeight_16",
    "head_cm1_color_head_wm1_squintInner_L": "maskWeight_17",
    "head_cm1_color_head_wm1_blink_R": "maskWeight_20",
    "head_cm1_color_head_wm1_squintInner_R": "maskWeight_21",
    "head_cm3_color_head_wm3_cheekRaiseInner_L": "maskWeight_24",
    "head_cm3_color_head_wm3_cheekRaiseOuter_L": "maskWeight_25",
    "head_cm3_color_head_wm3_cheekRaiseUpper_L": "maskWeight_26",
    "head_cm3_color_head_wm3_cheekRaiseInner_R": "maskWeight_30",
    "head_cm3_color_head_wm3_cheekRaiseOuter_R": "maskWeight_31",
    "head_cm3_color_head_wm3_cheekRaiseUpper_R": "maskWeight_32",
    "head_cm2_color_head_wm2_noseWrinkler_L": "maskWeight_36",
    "head_cm2_color_head_wm2_noseWrinkler_R": "maskWeight_38",
    "head_cm3_color_head_wm3_smile_L": "maskWeight_40",
    "head_cm1_color_head_wm13_lips_UL": "maskWeight_42",
    "head_cm1_color_head_wm13_lips_UR": "maskWeight_43",
    "head_cm1_color_head_wm13_lips_DL": "maskWeight_44",
    "head_cm1_color_head_wm13_lips_DR": "maskWeight_45",
    "head_cm3_color_head_wm3_smile_R": "maskWeight_50",
    "head_cm3_color_head_wm13_lips_UL": "maskWeight_52",
    "head_cm3_color_head_wm13_lips_DL": "maskWeight_53",
    "head_cm3_color_head_wm13_lips_UR": "maskWeight_56",
    "head_cm3_color_head_wm13_lips_DR": "maskWeight_57",
    "head_cm2_color_head_wm2_mouthStretch_L": "maskWeight_60",
    "head_cm2_color_head_wm2_mouthStretch_R": "maskWeight_62",
    "head_cm1_color_head_wm1_purse_UL": "maskWeight_64",
    "head_cm1_color_head_wm1_purse_UR": "maskWeight_66",
    "head_cm1_color_head_wm1_purse_DL": "maskWeight_68",
    "head_cm1_color_head_wm1_purse_DR": "maskWeight_70",
    "head_cm1_color_head_wm1_chinRaise_L": "maskWeight_72",
    "head_cm1_color_head_wm1_chinRaise_R": "maskWeight_74",
    "head_cm1_color_head_wm1_jawOpen": "maskWeight_76",
    "head_cm2_color_head_wm2_neckStretch_L": "maskWeight_78",
    "head_cm2_color_head_wm2_neckStretch_R": "maskWeight_80",
    "head_wm2_normal_head_wm2_browsDown_L": "maskWeight_01",
    "head_wm2_normal_head_wm2_browsDown_R": "maskWeight_03",
    "head_wm2_normal_head_wm2_browsLateral_L": "maskWeight_05",
    "head_wm2_normal_head_wm2_browsLateral_R": "maskWeight_07",
    "head_wm1_normal_head_wm1_browsRaiseInner_L": "maskWeight_09",
    "head_wm1_normal_head_wm1_browsRaiseInner_R": "maskWeight_11",
    "head_wm1_normal_head_wm1_browsRaiseOuter_L": "maskWeight_13",
    "head_wm1_normal_head_wm1_browsRaiseOuter_R": "maskWeight_15",
    "head_wm1_normal_head_wm1_blink_L": "maskWeight_18",
    "head_wm1_normal_head_wm1_squintInner_L": "maskWeight_19",
    "head_wm1_normal_head_wm1_blink_R": "maskWeight_22",
    "head_wm1_normal_head_wm1_squintInner_R": "maskWeight_23",
    "head_wm3_normal_head_wm3_cheekRaiseInner_L": "maskWeight_27",
    "head_wm3_normal_head_wm3_cheekRaiseOuter_L": "maskWeight_28",
    "head_wm3_normal_head_wm3_cheekRaiseUpper_L": "maskWeight_29",
    "head_wm3_normal_head_wm3_cheekRaiseInner_R": "maskWeight_33",
    "head_wm3_normal_head_wm3_cheekRaiseOuter_R": "maskWeight_34",
    "head_wm3_normal_head_wm3_cheekRaiseUpper_R": "maskWeight_35",
    "head_wm2_normal_head_wm2_noseWrinkler_L": "maskWeight_37",
    "head_wm2_normal_head_wm2_noseWrinkler_R": "maskWeight_39",
    "head_wm3_normal_head_wm3_smile_L": "maskWeight_41",
    "head_wm1_normal_head_wm13_lips_UL": "maskWeight_46",
    "head_wm1_normal_head_wm13_lips_UR": "maskWeight_47",
    "head_wm1_normal_head_wm13_lips_DL": "maskWeight_48",
    "head_wm1_normal_head_wm13_lips_DR": "maskWeight_49",
    "head_wm3_normal_head_wm3_smile_R": "maskWeight_51",
    "head_wm3_normal_head_wm13_lips_UL": "maskWeight_54",
    "head_wm3_normal_head_wm13_lips_DL": "maskWeight_55",
    "head_wm3_normal_head_wm13_lips_UR": "maskWeight_58",
    "head_wm3_normal_head_wm13_lips_DR": "maskWeight_59",
    "head_wm2_normal_head_wm2_mouthStretch_L": "maskWeight_61",
    "head_wm2_normal_head_wm2_mouthStretch_R": "maskWeight_63",
    "head_wm1_normal_head_wm1_purse_UL": "maskWeight_65",
    "head_wm1_normal_head_wm1_purse_UR": "maskWeight_67",
    "head_wm1_normal_head_wm1_purse_DL": "maskWeight_69",
    "head_wm1_normal_head_wm1_purse_DR": "maskWeight_71",
    "head_wm1_normal_head_wm1_chinRaise_L": "maskWeight_73",
    "head_wm1_normal_head_wm1_chinRaise_R": "maskWeight_75",
    "head_wm1_normal_head_wm1_jawOpen": "maskWeight_77",
    "head_wm2_normal_head_wm2_neckStretch_L": "maskWeight_79",
    "head_wm2_normal_head_wm2_neckStretch_R": "maskWeight_81",
}


def ls_shaders():
    sg_nodes = cmds.ls("shader_*SG")
    materials = cmds.ls("shader_*")
    materials = [i for i in materials if i not in sg_nodes]
    return materials, sg_nodes


def import_asset_materials(asset_dir, asset_name):
    """
from . import mhFaceMaterials
mhFaceMaterials.import_asset_materials("Omar")

    """
    file_path = os.path.join(
        asset_dir, asset_name, "SourceAssets", "{}_shaders.mb".format(asset_name)
    )

    if not os.path.exists(file_path):
        raise mhCore.MHError("file not found: {}".format(file_path))

    # import files
    print("Importing file: {}".format(file_path))
    cmds.file(file_path, i=True)

    # delete any redundant nodes
    duplicate_nodes = cmds.ls("{}_shaders_*".format(asset_name))

    materials, sg_nodes = ls_shaders()

    redundant_nodes = [i for i in materials if i not in MATERIAL_MAPPING]
    redundant_nodes += [i for i in sg_nodes if i[:-2] not in MATERIAL_MAPPING]
    redundant_nodes += duplicate_nodes

    if redundant_nodes:
        print("Deleting redundant nodes: {}".format(redundant_nodes))
        cmds.delete(redundant_nodes)

    return file_path


def export_asset_materials():
    # get materials
    materials = list(MATERIAL_MAPPING.keys())

    materials = [i for i in materials if cmds.objExists(i)]
    sg_nodes = ["{}SG".format(i) for i in materials]
    sg_nodes = [i for i in sg_nodes if cmds.objExists(i)]

    if not materials:
        raise mhCore.MHError("No metahuman materials found to export")

    # get paths
    scene_file_path = cmds.file(query=True, sceneName=True)

    scene_dir, scene_name = os.path.split(scene_file_path)

    asset_name = scene_name.split("_")[0]

    file_path = os.path.join(
        scene_dir, "{}_shaders.mb".format(asset_name)
    )

    # delete everything we don't want
    nodes = cmds.ls(assemblies=True)
    nodes = [i for i in nodes if i not in ["persp", "top", "front", "side"]]
    cmds.delete(nodes)

    # export file
    print("Exporting file: {} {}".format(file_path, materials + sg_nodes))
    cmds.select(materials + sg_nodes)
    # TODO debug why SG nodes aren't exporting
    cmds.file(file_path, exportSelected=True, type="mayaBinary")

    # reload original scene
    cmds.file(scene_file_path, open=True, force=True)

    return file_path


def apply_materials(lod=0):
    for material, meshes in MATERIAL_MAPPING.items():
        if not meshes:
            continue

        meshes = ["{}_lod{}_mesh".format(mesh, lod) for mesh in meshes]

        sg_node = "{}SG".format(material)

        if not cmds.objExists(sg_node):
            print("[ WARNING ] material shading group not found: {}".format(sg_node))
            continue

        cmds.sets(meshes, edit=True, forceElement=sg_node)

    return True

def connect_channels():
    src_node = "FRM_WMmultipliers"
    head_shader = "shader_head_shader"

    for src_attr, dst_attr in MATERIAL_CHANNEL_MAPPING.items():
        cmds.connectAttr(
            "{}.{}".format(src_node, src_attr),
            "{}.{}".format(head_shader, dst_attr)
        )

    return True

def reset_materials(lod=0, cleanup=True):
    for meshes in MATERIAL_MAPPING.values():
        if not meshes:
            continue

        meshes = ["{}_lod{}_mesh".format(mesh, lod) for mesh in meshes]
        cmds.sets(meshes, edit=True, forceElement="initialShadingGroup")

    if cleanup:
        materials, sg_nodes = ls_shaders()

        for material in materials:
            con = cmds.listConnections(material)

            if "defaultShaderList1" in con:
                con.remove("defaultShaderList1")

            cmds.delete(material, con)

    return True

def find_paths(folder_name):
    """
from brenmeta import mhFaceMaterials
paths = mhFaceMaterials.find_paths("Common")

    """

    paths = cmds.filePathEditor(query=True, listDirectories="", relativeNames=True)

    if not paths:
        return None

    found_paths = set([])

    for path in paths:
        while True:
            parent_path, folder = os.path.split(path)

            if folder == folder_name:
                found_paths.add(path)
                break

            if not folder:
                break

            path = path[:-len(folder)-1]

    return list(found_paths)

def find_asset_paths():
    paths = find_paths("SourceAssets")

    found_paths = set([])

    for path in paths:
        path = os.path.split(path)[0]
        name = os.path.split(path)[1]

        if name != "Common":
            found_paths.add(path)

    return list(found_paths)
