import dna
import dnacalib

from maya import cmds

from . import mhMayaUtils

def get_vertex_positions_from_dna(dna_obj, reader, lod=0):

    if lod is None:
        mesh_indices = list(range(reader.getMeshCount()))
    else:
        mesh_indices = dna_obj.get_mesh_indices_for_lod(lod)

    if not mesh_indices:
        print("No meshes found in DNA.")
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
    print("getting dna mesh data...")
    mesh_data = get_vertex_positions_from_dna(dna_obj, calib_reader, lod=lod)
    meshes = dna_obj.meshes.names

    # get deltas and create commands
    commands = dnacalib.CommandSequence()

    for mesh_index, existing_positions in enumerate(mesh_data):
        mesh = meshes[mesh_index]

        if not cmds.objExists(mesh):
            print("mesh not found in scene: {}".format(mesh))
            continue

        # TODO check vertex counts are the same

        print("updating mesh: {}".format(mesh))

        scene_vertex_positions = mhMayaUtils.get_points(mesh, as_positions=True)

        deltas = [
            [a[i]-b[i] for i in range(3)]
            for a, b in zip(scene_vertex_positions, existing_positions)
        ]

        command = dnacalib.SetVertexPositionsCommand(
            mesh_index, deltas, dnacalib.VectorOperation_Add
        )

        commands.add(command)

    print("running commands...")
    commands.run(calib_reader)

    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError(status.message)

    return True


def calculate_lods(dna_obj, calib_reader, from_lod=0):
    # get existing mesh data
    meshes = dna_obj.meshes.names

    # create commands
    commands = dnacalib.CommandSequence()

    for mesh_index in dna_obj.get_mesh_indices_for_lod(from_lod):
        mesh = meshes[mesh_index]

        print("calculating lods: {}".format(mesh))
        calculate_lods_command = dnacalib.CalculateMeshLowerLODsCommand()
        calculate_lods_command.setMeshIndex(mesh_index)
        commands.add(calculate_lods_command)

    print("running commands...")
    commands.run(calib_reader)

    # Verify that everything went fine
    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError(status.message)

    return True
