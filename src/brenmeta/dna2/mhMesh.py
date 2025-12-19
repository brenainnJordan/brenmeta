import dna
import dnacalib2

from maya import cmds

from brenmeta.maya import mhMayaUtils
from brenmeta.core import mhCore

LOG = mhCore.get_basic_logger(__name__)


def get_mesh_indices(dna_obj, reader, lod=None):
    if lod is None:
        mesh_indices = list(range(reader.getMeshCount()))
    else:
        mesh_indices = dna_obj.get_mesh_indices_for_lod(lod)

    return mesh_indices

def get_vertex_positions_from_dna(dna_obj, reader, lod=0):

    mesh_indices = get_mesh_indices(dna_obj, reader, lod=lod)

    if not mesh_indices:
        LOG.info("No meshes found in DNA.")
        return None

    mesh_vertex_positions = []

    for mesh_index in mesh_indices:
        xs = reader.getVertexPositionXs(mesh_index)
        ys = reader.getVertexPositionYs(mesh_index)
        zs = reader.getVertexPositionZs(mesh_index)

        positions = [
            [x,y,z] for x,y,z in zip(xs, ys, zs)
        ]

        mesh_vertex_positions.append(positions)

    return mesh_vertex_positions


def update_meshes_from_scene(dna_obj, calib_reader, lod=0):

    # get existing mesh data
    LOG.info("getting dna mesh data...")
    mesh_data = get_vertex_positions_from_dna(dna_obj, calib_reader, lod=lod)
    meshes = dna_obj.get_meshes()

    # get deltas and create commands
    commands = dnacalib2.CommandSequence()

    for mesh_index, existing_positions in enumerate(mesh_data):
        mesh = meshes[mesh_index].name

        if not cmds.objExists(mesh):
            LOG.info("mesh not found in scene: {}".format(mesh))
            continue

        # TODO check vertex counts are the same

        LOG.info("updating mesh: {}".format(mesh))

        scene_vertex_positions = mhMayaUtils.get_points(mesh, as_positions=True)

        deltas = [
            [a[i]-b[i] for i in range(3)]
            for a, b in zip(scene_vertex_positions, existing_positions)
        ]

        command = dnacalib2.SetVertexPositionsCommand(
            mesh_index, deltas, dnacalib2.VectorOperation_Add
        )

        commands.add(command)

    LOG.info("running commands...")
    commands.run(calib_reader)

    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError(status.message)

    return True


def calculate_lods(dna_obj, calib_reader, from_lod=0):
    # get existing mesh data
    meshes = dna_obj.get_meshes()

    # create commands
    commands = dnacalib2.CommandSequence()

    for mesh_index in dna_obj.get_mesh_indices_for_lod(from_lod):
        mesh = meshes[mesh_index]

        LOG.info("calculating lods: {}".format(mesh.name))
        calculate_lods_command = dnacalib2.CalculateMeshLowerLODsCommand()
        calculate_lods_command.setMeshIndex(mesh_index)
        commands.add(calculate_lods_command)

    LOG.info("running commands...")
    commands.run(calib_reader)

    # Verify that everything went fine
    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError(status.message)

    return True

def get_blendshape_deltas(dna_obj, reader, lod=0):
    # TODO finish this
    if lod is None:
        mesh_indices = list(range(reader.getMeshCount()))
    else:
        mesh_indices = dna_obj.get_mesh_indices_for_lod(lod)

    if not mesh_indices:
        LOG.info("No meshes found in DNA.")
        return None

    for mesh_index in mesh_indices:
        target_count = reader.getBlendShapeTargetCount(mesh_index)

        for target_index in range(target_count):
            delta_count = reader.getBlendShapeTargetDeltaCount(mesh_index, target_index)

            for delta_index in range(delta_count):
                delta = reader.getBlendShapeTargetDelta(mesh_index, target_index, delta_index)

    return True

def set_blendshape_deltas():
    # TODO
    dnacalib2.SetBlendShapeTargetDeltasCommand

def scale_all_blendshape_deltas():
    pass

def merge_meshes_positions(src_dna_obj, src_calib_reader, dst_dna_obj, dst_calib_reader, lod=0):

    # get existing mesh data
    LOG.info("getting dna mesh data...")

    src_mesh_data = get_vertex_positions_from_dna(src_dna_obj, src_calib_reader, lod=lod)
    src_meshes = src_dna_obj.get_meshes()

    dst_mesh_data = get_vertex_positions_from_dna(dst_dna_obj, dst_calib_reader, lod=lod)
    dst_meshes = dst_dna_obj.get_meshes()

    # get deltas and create commands
    commands = dnacalib2.CommandSequence()

    for mesh_index in src_dna_obj.get_mesh_indices_for_lod(lod):
        mesh = src_meshes[mesh_index].name

        LOG.info("updating mesh: {}".format(mesh))

        src_positions = src_mesh_data[mesh_index]
        dst_positions = dst_mesh_data[mesh_index]

        deltas = [
            [a[i]-b[i] for i in range(3)]
            for a, b in zip(src_positions, dst_positions)
        ]

        command = dnacalib2.SetVertexPositionsCommand(
            mesh_index, deltas, dnacalib2.VectorOperation_Add
        )

        commands.add(command)

    LOG.info("running commands...")
    commands.run(dst_calib_reader)

    if not dna.Status.isOk():
        status = dna.Status.get()
        raise mhCore.MHError(status.message)

    return True
