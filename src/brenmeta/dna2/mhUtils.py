import os

from maya import cmds

import dnacalib2
import dna
import mh_character_assembler

from mh_assemble_lib.model.dnalib import DNAReader, Layer
from mh_assemble_lib.control.form import MeshForm, ProcessForm
from mh_assemble_lib.impl.maya.handler import MayaHandler
from mh_assemble_lib.impl.maya.properties import MayaSceneOrient

from brenmeta.core import mhCore

def import_components(
        dna_path,
        assets_path,
        add_joints=True,
        add_rig_logic=True,
        add_skin_cluster=True,
        add_blend_shapes=True,
        lod=None,
        scene_up="y",
):
    dna_reader = DNAReader.read(dna_path, Layer.all)

    handler = MayaHandler()

    if scene_up == "z":
        handler.config.scene_orient = MayaSceneOrient.get_head_z_up_orient()
    else:
        handler.config.scene_orient = MayaSceneOrient.get_head_y_up_orient()

    form = ProcessForm()

    # set meshes to import
    form.meshes = []

    if lod is None:
        # add all LODs
        for mesh_id in range(dna_reader.get_mesh_count()):
            mesh_name = dna_reader.get_mesh_name(mesh_id)
            form.meshes.append(MeshForm(mesh_id, mesh_name))
    else:
        mesh_ids = dna_reader.get_mesh_indices_for_lod(lod)

        for mesh_id in mesh_ids:
            mesh_name = dna_reader.get_mesh_name(mesh_id)
            form.meshes.append(MeshForm(mesh_id, mesh_name))

    # set rig components to build
    form.add_joints = add_joints
    form.add_rig_logic = add_rig_logic
    form.add_skin_cluster = add_skin_cluster
    form.add_blend_shapes = add_blend_shapes

    # set dependencies
    if add_rig_logic:
        form.gui_ctrls_path = os.path.join(assets_path, "Windows", "head_gui.ma")
        form.analog_ctrls_path = os.path.join(assets_path, "Windows", "head_ac.ma")

        form.aas_path = os.path.join(
            assets_path, "additional_assemble_script.py",
        )

        # check dependencies exist before building
        for file_path in [
            form.gui_ctrls_path,
            form.analog_ctrls_path,
            form.aas_path
        ]:
            if not os.path.exists(file_path):
                raise mhCore.MHError("Dependency file not found: {}".format(file_path))

    # build
    handler.set_state(dna_reader, form)
    handler.build_mh()

    return True
