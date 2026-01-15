"""Supporting maya utilities
"""

import json
import os

from maya.api import OpenMaya
from maya.api import OpenMayaAnim
from maya import cmds

from brenmeta.core import mhCore

LOG = mhCore.get_basic_logger(__name__)

def break_connections(attrs):
    if not isinstance(attrs, (list, tuple)):
        attrs = [attrs]

    for attr in attrs:
        cons = cmds.listConnections(
            attr, source=True, destination=False, plugs=True
        )

        if not cons:
            continue

        cmds.disconnectAttr(cons[0], attr)

    return True


def parse_m_object(value, api_type=None, check_valid=True):
    """Parse a given user value and return MObject

    Checks api type if given.

    :param value: str, OpenMaya.MObject, OpenMaya.MDagPath, OpenMaya.MFnBase subclass
    :param api_type: None, MFn type enum (eg. OpenMaya.MFn.kTransform)
    :return: OpenMaya.MObject
    """

    if api_type is not None:
        if not isinstance(api_type, (list,tuple)):
            api_type = [api_type]

        for i, api_type_i in enumerate(api_type):
            mhCore.validate_arg("api_type[{}]".format(i), api_type_i, int)

    # get MObject
    if isinstance(value, OpenMaya.MObject):
        m_object = value

    elif isinstance(value, OpenMaya.MDagPath):
        m_object = value.node()

    elif isinstance(value, OpenMaya.MFnBase):
        m_object = value.object()

    elif isinstance(value, str):
        sel = OpenMaya.MSelectionList()

        try:
            sel.add(value)
        except RuntimeError as err:
            raise mhCore.MHError("{} ({})".format(str(err), value))

        m_object = sel.getDependNode(0)

    else:
        raise mhCore.MHError("MObject value not recognized: {}".format(value))

    # check type
    if api_type is not None:
        if not m_object.apiType() in api_type:
            raise mhCore.MHError(
                "MObject api type ({} {} {}) not expected value: {}".format(
                    value, m_object.apiTypeStr, m_object.apiType(), api_type
                )
            )

    # check valid
    if check_valid:
        if m_object.isNull():
            raise mhCore.MHError("MObject invalid: {}".format(value))

    return m_object


def parse_dag_path(dag_path):
    if isinstance(dag_path, OpenMaya.MDagPath):
        return dag_path

    elif isinstance(dag_path, str):
        if not cmds.objExists(dag_path):
            raise mhCore.MHError("Node not found: {}".format(dag_path))

        sel = OpenMaya.MSelectionList()
        sel.add(dag_path)
        return sel.getDagPath(0)
    else:
        raise mhCore.MHError("dag path not recognised: {}".format(dag_path))


def parse_dag_path(value, api_type=None, check_valid=True):
    """Parse a given user value and return MDagPath

    Checks api type if given.

    :param value: str, OpenMaya.MFnDagNode, OpenMaya.MDagPath
    :param api_type: None, MFn type enum (eg. OpenMaya.MFn.kTransform)
    :return: OpenMaya.MDagPath
    """

    mhCore.validate_arg("api_type", api_type, int, can_be_none=True)

    # get MDagPath
    if isinstance(value, OpenMaya.MObject):
        # attempt to instance an MFnDagNode
        # this will error if MObject isn't a dag object
        mfn = OpenMaya.MFnDagNode(value)
        return mfn.getPath()

    elif isinstance(value, OpenMaya.MDagPath):
        m_dag_path = value

    elif isinstance(value, OpenMaya.MFnDagNode):
        # m_dag_path = value.dagPath()
        # note ideally we would use dagPath()
        # assuming that the Mfn object had been constructed properly
        # (ie bound to a MDagPath object)
        # but because we allow the user to construct their own MFn object
        # we can't guarantee that it's bound to a MDagPath object
        # so lets use getPath() instead.
        # return MFnDagNode.dagPath()
        return value.getPath()

    elif isinstance(value, str):

        sel = OpenMaya.MSelectionList()

        try:
            sel.add(value)
        except RuntimeError as err:
            raise mhCore.MHError("{} ({})".format(str(err), value))

        try:
            m_dag_path = sel.getDagPath(0)
        except TypeError as err:
            raise mhCore.MHError("{} ({})".format(str(err), value))

    else:
        raise mhCore.MHError("Dag path value not recognized: {}".format(value))

    # check type
    if api_type is not None:
        if m_dag_path.apiType() != api_type:
            raise mhCore.MHError(
                "MDagPath api type ({} {}) not expected value: {}".format(
                    m_dag_path.node().apiTypeStr, m_dag_path.apiType(), api_type
                )
            )

    # check valid
    if check_valid:
        if not m_dag_path.isValid():
            raise mhCore.MHError("MDagPath invalid: {}".format(value))

        if m_dag_path.node().isNull():
            raise mhCore.MHError("MObject invalid: {}".format(value))

    return m_dag_path


def get_all_component_list_elements(component_list):
    """
    Note we just append to the list instead of using a set
    because we want to keep the component order
    and sets are un-ordered

    """
    mhCore.validate_arg("component_list", component_list, OpenMaya.MFnComponentListData)

    all_elements = []

    for i in range(component_list.length()):
        component = component_list.get(i)
        component = OpenMaya.MFnSingleIndexedComponent(component)
        elements = component.getElements()
        all_elements += elements

    return all_elements


def get_points(mesh, space=OpenMaya.MSpace.kWorld, as_positions=False, as_vector=False):
    # get dag
    dag = parse_dag_path(mesh)

    # get points
    m_mesh = OpenMaya.MFnMesh(dag)
    m_points = m_mesh.getPoints(space=space)

    if as_positions:
        return [list(i)[:3] for i in m_points]

    elif as_vector:
        return [OpenMaya.MVector(i) for i in m_points]

    else:
        return m_points


def get_orig_mesh(deformer, as_name=True):
    deformer_m_object = parse_m_object(
        deformer,
        # api_type=OpenMaya.MFn.kBlendShape
    )

    deformer_fn = OpenMayaAnim.MFnGeometryFilter(deformer_m_object)

    mesh_object = deformer_fn.getInputGeometry()[0]

    if as_name:
        mesh_fn = OpenMaya.MFnMesh(mesh_object)
        return mesh_fn.name()
    else:
        return mesh_object


def get_average_position(positions):
    average_position = []
    count = len(positions)

    for axis_index in range(3):
        axis_values = [position[axis_index] for position in positions]
        average = sum(axis_values) / count
        average_position.append(average)

    return average_position


def get_closest_point_index(point, point_array, max_distance=None):
    distances = [
        point.distanceTo(i) for i in point_array
    ]

    nearest_index = distances.index(min(distances))

    if max_distance is not None:
        if distances[nearest_index] > max_distance:
            return None

    return nearest_index


def get_closest_vertices(positions, mesh, max_distance=None):
    points = get_points(mesh)

    positions = [
        OpenMaya.MPoint(i) for i in positions
    ]

    nearest_indices = [
        get_closest_point_index(position, points, max_distance=max_distance)
        for position in positions
    ]

    return nearest_indices


def get_leaf_transforms(root_transform, **kwargs):
    child_transforms = cmds.listRelatives(root_transform, **kwargs)

    if not child_transforms:
        return None

    leaf_transforms = [
        child_transform for child_transform in child_transforms
        if not cmds.listRelatives(child_transform, **kwargs)
    ]

    return leaf_transforms


def xform_preserve_children(transform, **kwargs):
    child_transforms = cmds.listRelatives(transform) or []
    child_matrices = [cmds.xform(i, query=True, matrix=True, worldSpace=True) for i in child_transforms]

    cmds.xform(transform, **kwargs)

    for child, matrix in zip(child_transforms, child_matrices):
        cmds.xform(child, matrix=matrix, worldSpace=True)

    return True


def create_aim_matrix_from_positions(position, aim_position, up_position, aim_vector, up_vector):
    aim_vector = OpenMaya.MVector(aim_vector)
    up_vector = OpenMaya.MVector(up_vector)

    position = OpenMaya.MVector(position)
    aim_position = OpenMaya.MVector(aim_position)
    up_position = OpenMaya.MVector(up_position)

    aim_target_vector = (aim_position - position).normal()
    up_target_vector = (up_position - position).normal()

    side_target_vector = up_target_vector ^ aim_target_vector
    up_target_vector = aim_target_vector ^ side_target_vector

    aim_rotation = aim_vector.rotateTo(aim_target_vector)

    up_vector = up_vector.rotateBy(aim_rotation)

    angle = up_vector.angle(up_target_vector)

    up_about_axis = up_vector ^ up_target_vector
    up_about_axis.normalize()

    up_rotation = OpenMaya.MQuaternion(angle, up_about_axis)

    rotation = aim_rotation * up_rotation

    matrix = rotation.asMatrix()

    for column, value in enumerate(position):
        matrix.setElement(3, column, value)

    return matrix


def transpose_matrix(matrix):
    row_count = len(matrix)
    column_count = len(matrix[0])

    transposed_matrix = [
        [matrix[row][column] for row in range(row_count)]
        for column in range(column_count)
    ]

    return transposed_matrix


def add_wrap_influence(wrap_node, influence):
    # add influence
    influenceShape = cmds.listRelatives(influence)[0]

    base = cmds.duplicate(influence, name=influence + 'Base')[0]
    baseShape = cmds.listRelatives(base)[0]

    # hide base mesh
    cmds.setAttr('{0}.v'.format(base), lock=False)
    cmds.setAttr('{0}.v'.format(base), 0)

    # create dropoff attr if it doesn't exist
    if not cmds.attributeQuery('dropoff', node=influence, exists=True):
        cmds.addAttr(influence, longName='dropoff', dv=4.0, min=0.0, max=20.0, k=True)

    # if type mesh
    # create smoothness attr if it doesn't exist
    if not cmds.attributeQuery('smoothness', node=influence, exists=True):
        cmds.addAttr(influence, sn='smt', ln='smoothness', dv=0.0, min=0.0, k=1)

    # create the inflType attr if it doesn't exist
    if not cmds.attributeQuery('inflType', n=influence, exists=True):
        cmds.addAttr(influence, at='short', sn='ift', ln='inflType', dv=2, min=1, max=2)

    cmds.connectAttr('{0}.worldMesh'.format(influenceShape), '{0}.driverPoints[0]'.format(wrap_node))
    cmds.connectAttr('{0}.worldMesh'.format(baseShape), '{0}.basePoints[0]'.format(wrap_node))
    cmds.connectAttr('{0}.inflType'.format(influence), '{0}.inflType[0]'.format(wrap_node))
    cmds.connectAttr('{0}.smoothness'.format(influence), '{0}.smoothness[0]'.format(wrap_node))

    cmds.connectAttr('{0}.dropoff'.format(influence), '{0}.dropoff[0]'.format(wrap_node))

    return True


def create_wrap(
        geos,
        influence,
        attrs=dict(weightThreshold=0,
                   maxDistance=0.0,
                   exclusiveBind=True,
                   autoWeightThreshold=False,
                   falloffMode=0)
):
    if not isinstance(geos, list):
        geos = [geos]

    shape_components = dict()
    for geo in geos:
        geo = geo
        comp = None
        if '.' in geo:
            comp = geo
            geo = geo.split('.')[0]
        elif cmds.objectType(geo, isAType='transform'):
            geo = cmds.listRelatives(geo, shapes=True, path=True, type='deformableShape', noIntermediate=True)[0]
        if geo in shape_components:
            if comp is None:
                shape_components[geo] = None
            else:
                shape_components[geo].add(comp)
        else:
            shape_components[geo] = None if comp is None else {comp}

    _wrap_nodes = []
    for shape, comps in shape_components.items():
        wrap = cmds.deformer(shape if comps is None else list(comps), type='wrap',
                             n='{0}_WRP'.format('_'.join(shape.split('_')[0:-1])))
        if wrap:
            wrap = wrap[0]
            for attr, value in attrs.items():
                cmds.setAttr('{0}.{1}'.format(wrap, attr), value)

            cmds.connectAttr('{0}.worldMatrix[0]'.format(shape), '{0}.geomMatrix'.format(wrap))

            add_wrap_influence(wrap, influence)

            _wrap_nodes.append(wrap)

    return _wrap_nodes


def edges_to_vertex_ids(mesh, edge_ids):
    mesh_dag = parse_dag_path(mesh)

    # convert to vertex ids
    edge_it = OpenMaya.MItMeshEdge(mesh_dag)

    vert_ids = set([])

    for i in edge_ids:
        edge_it.setIndex(i)
        vert_ids.add(edge_it.vertexId(0))
        vert_ids.add(edge_it.vertexId(1))

    vert_ids = list(vert_ids)

    return vert_ids


def get_furthest_intersection(mesh_fn, ray_start, ray_vector, both_directions=False, max_distance=10000):
    hit_data = mesh_fn.allIntersections(
        ray_start,
        ray_vector,
        OpenMaya.MSpace.kWorld,
        max_distance,
        both_directions,
    )

    if hit_data is None:
        return None

    params = list(hit_data[1])
    max_distance_index = params.index(max(params))

    result = [i[max_distance_index] for i in hit_data]

    # bugfix to avoid maya overwriting stuff in memory (wierd!!!)
    result[0] = OpenMaya.MPoint(list(result[0]))

    return result


def export_meshes_to_objs(meshes, directory, prefix="", suffix="", overwrite=False, verbose=True):
    """
    TODO metadata file
    """
    for mesh in meshes:
        if "|" in mesh:
            mesh_name = mesh.split("|")[-1]
        else:
            mesh_name = str(mesh)

        file_path = os.path.join(
            directory,
            "{}{}{}.obj".format(prefix, mesh_name, suffix)
        )

        if os.path.exists(file_path) and not overwrite:
            raise Exception("File already exists: {}".format(file_path))

        if verbose:
            LOG.info("Exporting mesh: {} - {}".format(mesh, file_path))

        cmds.select(mesh)

        cmds.file(
            file_path,
            force=True,
            options="groups=1;ptgroups=1;materials=0;smoothing=1;normals=1",
            typ="OBJexport",
            exportSelected=True
        )

    cmds.select(meshes)

    if verbose:
        LOG.info("All meshes exported to: {}".format(directory))

    return True


def import_objs(directory, prefix=None, verbose=True):

    # get obj files
    contents = os.listdir(directory)

    file_paths = []

    for item in contents:
        path = os.path.join(directory, item)

        if not os.path.isfile(path):
            continue

        if not path.lower().endswith(".obj"):
            continue

        file_paths.append(path)

    # import objs
    if prefix:
        file_kwargs = {
            "renameAll": True,
            "renamingPrefix": prefix,
        }
    else:
        file_kwargs = {}

    for file_path in file_paths:
        if verbose:
            LOG.info("Importing file: {}".format(file_path))

        result = cmds.file(
            file_path,
            i=True,
            type="OBJ",
            **file_kwargs
        )

    return True
