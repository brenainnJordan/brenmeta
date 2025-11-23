"""
paths:
C:\Program Files\Epic Games\MetaHumanForMaya\lib\mh_character_assembler\1.1.3\mh_character_assembler
C:\Program Files\Epic Games\MetaHumanForMaya\lib\mh_assemble_lib\0.7.2\mh_assemble_lib
C:\Program Files\Epic Games\MetaHumanForMaya\lib\mh_assemble_lib\0.7.2\mh_assemble_lib\impl\maya


"""

import os

from maya import cmds

cmds.loadPlugin("embeddedRL4")

import dnacalib2

import dna

import mh_character_assembler

from frt_api.maya.skin_weights import SkinWeightsMayaHandler
from mh_character_assembler.importer import CharacterImporter
from mh_character_assembler.config import Config
from mh_assemble_lib.model.dnalib import DNAReader, Layer
from mh_assemble_lib.control.form import MeshForm, ProcessForm
from mh_assemble_lib.impl.maya.handler import MayaHandler
from mh_assemble_lib.impl.maya.properties import MayaSceneOrient

mh_path = r"D:\Projects\3d\metahuman\chloe\MHC_DCC_Export\MHC_chloe"
head_dna_path = r"D:\Projects\3d\metahuman\chloe\MHC_DCC_Export\MHC_chloe\head.dna"

def import_char_prompted():
    config_data = {
        "bodyDnaPath": f"{mh_path}\\body.dna",
        "mapsDirPath": f"{mh_path}\\Maps\\",
        "headDnaPath": f"{mh_path}\\head.dna",
    }

    options = {
        "import_head": True,
        "import_body": False,
        "import_textures": True,
        "scene_orientation": "Y",
    }

    # create with prompt
    CharacterImporter().execute(config, options)


def import_char_unprompted():
    # create without prompt
    char_importer = CharacterImporter()

    config = Config(config_data)

    config.options.import_head = options["import_head"]
    config.options.import_body = options["import_body"]
    config.options.import_textures = options["import_textures"]

    config.scene_orientation_string_value = options["scene_orientation"]
    config.scene_orientation = config.resolve_scene_orientation()

    char_importer.config = config

    char_importer.logger.info(config)
    char_importer.assemble()


def import_components(
        dna_path,
        add_joints=True,
        add_rig_logic=True,
        add_skin_cluster=True,
        add_blend_shapes=True,
        scene_up="y",
        dna_version="MH.6"
):
    dna_reader = DNAReader.read(dna_path, Layer.all)

    handler = MayaHandler()

    if scene_up == "z":
        handler.config.scene_orient = MayaSceneOrient.get_head_z_up_orient()
    else:
        handler.config.scene_orient = MayaSceneOrient.get_head_y_up_orient()

    form = ProcessForm()
    form.add_joints = add_joints
    form.add_rig_logic = add_rig_logic
    form.add_skin_cluster = add_skin_cluster
    form.add_blend_shapes = add_blend_shapes

    assets_path = os.path.join(
        os.path.dirname(os.path.abspath(mh_character_assembler.__file__)),
        "assets",
        dna_version,
    )

    form.gui_ctrls_path = os.path.join(assets_path, "Windows", "head_gui.ma")
    form.analog_ctrls_path = os.path.join(assets_path, "Windows", "head_ac.ma")

    form.aas_path = os.path.join(
        assets_path, "additional_assemble_script.py",
    )

    form.meshes = []

    for mesh_id in range(dna_reader.get_mesh_count()):
        mesh_name = dna_reader.get_mesh_name(mesh_id)
        form.meshes.append(MeshForm(mesh_id, mesh_name))

    handler.set_state(dna_reader, form)
    handler.build_mh()
