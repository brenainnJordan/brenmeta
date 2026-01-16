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

def scale_dna(reader, scale):
    scale_cmd = dnacalib2.ScaleCommand(scale, [0, 0, 0])
    scale_cmd.run(reader)
    return True


def load_dna(path):
    """
    """
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
    reader = dna.BinaryStreamReader(stream, Layer.all.value)
    reader.read()
    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError("Error loading DNA: {}".format(status.message))
    return reader


def save_dna(reader, path, validate=True, as_json=False):
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Write, dna.FileStream.OpenMode_Binary)

    if as_json:
        writer = dna.JSONStreamWriter(stream)
    else:
        writer = dna.BinaryStreamWriter(stream)

    writer.setFrom(reader)

    writer.write()

    if validate:
        if not dna.Status.isOk():
            status = dna.Status.get()
            raise RuntimeError("Error saving DNA: {}".format(status.message))

    return True


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
    dna_obj = DNAReader.read(dna_path, Layer.all)

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
        for mesh_id in range(dna_obj.get_mesh_count()):
            mesh_name = dna_obj.get_mesh_name(mesh_id)
            form.meshes.append(MeshForm(mesh_id, mesh_name))
    else:
        mesh_ids = dna_obj.get_mesh_indices_for_lod(lod)

        for mesh_id in mesh_ids:
            mesh_name = dna_obj.get_mesh_name(mesh_id)
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
    handler.set_state(dna_obj, form)
    handler.build_mh()

    return True
