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

import math

from maya import cmds
from maya.api import OpenMaya

from brenmeta.core import mhCore
from brenmeta.maya import mhMayaUtils


def snap_joints_to_vertex_ids(mesh, mapped_joints):
    points = mhMayaUtils.get_points(mesh, as_positions=True)

    for joint, vertex_id in mapped_joints.items():
        mhMayaUtils.xform_preserve_children(
            joint, translation=points[vertex_id], worldSpace=True
        )

    return True


def get_joint_offset_from_mesh(joint, mesh, vector, max_distance=10000, both_directions=False):
    """use closestIntersection to raycast onto mesh and get distances
    """
    mesh_dag = mhMayaUtils.parse_dag_path(mesh)
    mesh_fn = OpenMaya.MFnMesh(mesh_dag)

    m_vector = OpenMaya.MFloatVector(vector)

    joint_position = cmds.xform(joint, query=True, translation=True, worldSpace=True)
    joint_matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=True)

    m_matrix = OpenMaya.MFloatMatrix(joint_matrix)

    ray_direction = m_vector * m_matrix

    intersection = mesh_fn.closestIntersection(
        OpenMaya.MFloatPoint(joint_position),
        ray_direction,
        OpenMaya.MSpace.kWorld,
        max_distance,
        both_directions,
        # faceIds=None, triIds=None, idsSorted=False,
        # accelParams=None, tolerance=kIntersectTolerance
    )

    # (hitPoint, hitRayParam, hitFace, hitTriangle, hitBary1, hitBary2)
    if intersection is None:
        raise mhCore.MHError("No intersection found: {}".format(joint))

    offset = intersection[1]

    return offset


def offset_joint_from_mesh(joint, mesh, offset):
    mesh_dag = mhMayaUtils.parse_dag_path(mesh)
    mesh_fn = OpenMaya.MFnMesh(mesh_dag)

    joint_position = cmds.xform(joint, query=True, translation=True, worldSpace=True)

    # use closest point
    joint_point = OpenMaya.MPoint(joint_position)

    closest_point, closest_normal, face_id = mesh_fn.getClosestPointAndNormal(
        joint_point, OpenMaya.MSpace.kWorld
    )

    closest_vector = OpenMaya.MVector(closest_point - joint_point)
    closest_vector.normalize()

    # check if point is above mesh surface
    if math.degrees(closest_vector.angle(closest_normal)) > 90.0:
        closest_vector *= -1.0

    # offset
    offset_vector = closest_vector * offset
    offset_point = OpenMaya.MPoint(offset_vector)
    offset_point = closest_point - offset_point

    mhMayaUtils.xform_preserve_children(
        joint, translation=list(offset_point)[:3], worldSpace=True
    )

    return True


def snap_joint_to_child_average(joint):
    child_joints = cmds.listRelatives(joint, type="joint")

    child_positions = [
        cmds.xform(child, query=True, translation=True, worldSpace=True)
        for child in child_joints
    ]

    avg_position = mhMayaUtils.get_average_position(child_positions)

    mhMayaUtils.xform_preserve_children(
        joint, translation=avg_position, worldSpace=True
    )

    return True


def map_joint_axes_to_mesh(
        joint, mesh, aim_vector, up_vector, closest_vertices=True, max_distance=10000, furthest=True
):
    """Project axes onto mesh and get closest points that can be mapped to another mesh
    TODO if not closest vertices then use bary coordinates
    """
    mesh_dag = mhMayaUtils.parse_dag_path(mesh)
    mesh_fn = OpenMaya.MFnMesh(mesh_dag)

    joint_position = cmds.xform(joint, query=True, translation=True, worldSpace=True)
    joint_position = OpenMaya.MFloatPoint(joint_position)

    joint_matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=True)
    m_matrix = OpenMaya.MFloatMatrix(joint_matrix)

    aim_vector = OpenMaya.MFloatVector(aim_vector) * m_matrix
    up_vector = OpenMaya.MFloatVector(up_vector) * m_matrix
    up_inverse_vector = up_vector * -1.0

    if furthest:
        aim_hit = mhMayaUtils.get_furthest_intersection(mesh_fn, joint_position, aim_vector)
        up_hit = mhMayaUtils.get_furthest_intersection(mesh_fn, joint_position, up_vector)
        up_inverse_hit = mhMayaUtils.get_furthest_intersection(mesh_fn, joint_position, up_inverse_vector)


    else:
        aim_hit = mesh_fn.closestIntersection(
            joint_position,
            aim_vector,
            OpenMaya.MSpace.kWorld, max_distance, False
        )

        up_hit = mesh_fn.closestIntersection(
            joint_position,
            up_vector,
            OpenMaya.MSpace.kWorld, max_distance, False
        )

        up_inverse_hit = mesh_fn.closestIntersection(
            joint_position,
            up_inverse_vector,
            OpenMaya.MSpace.kWorld, max_distance, False
        )

    if any([aim_hit is None, up_hit is None, up_inverse_hit is None]):
        raise mhCore.MHError("No intersections found: {}".format(joint))

    # check up hits face ids
    if up_hit[2] == up_inverse_hit[2]:
        raise mhCore.MHError("up intersections returned same face: {}".format(joint))

    if closest_vertices:
        hit_positions = [list(i)[:3] for i in [aim_hit[0], up_hit[0], up_inverse_hit[0]]]

        result = mhMayaUtils.get_closest_vertices(
            hit_positions,
            mesh_dag
        )

    else:
        raise NotImplementedError()

    return result


def snap_joint_to_axes_data(
        joint, mesh, data, position_only=False, aim_vector=None, up_vector=None, preserve_children=True
):
    """
    TODO aim and up vector
    :param joint:
    :param mesh:
    :param data:
    :param aim_vector:
    :param up_vector:
    :return:
    """
    points = mhMayaUtils.get_points(mesh)

    aim_point = OpenMaya.MVector(points[data[0]])
    side_point = OpenMaya.MVector(points[data[1]])
    side_inverse_point = OpenMaya.MVector(points[data[2]])

    avg_point = mhMayaUtils.get_average_position([side_point, side_inverse_point])

    avg_point = OpenMaya.MVector(avg_point)

    if position_only:
        if preserve_children:
            mhMayaUtils.xform_preserve_children(
                joint, translation=list(avg_point), worldSpace=True
            )
        else:
            cmds.xform(
                joint, translation=list(avg_point), worldSpace=True
            )

        return True

    # get aim matrix
    matrix = mhMayaUtils.create_aim_matrix_from_positions(
        avg_point, aim_point, side_point, aim_vector=aim_vector, up_vector=up_vector
    )

    # xform
    if preserve_children:
        mhMayaUtils.xform_preserve_children(joint, matrix=list(matrix), worldSpace=True)
    else:
        cmds.xform(joint, matrix=list(matrix), worldSpace=True)

    return True


def get_joint_matrices_from_scene(joints, world_space=True):
    # if reader:
    #     joints = [
    #         reader.getJointName(i) for i in range(reader.getJointCount())
    #     ]
    # else:
    #     joints = cmds.ls(type="joint")

    matrices = {}

    for joint in joints:
        if not cmds.objExists(joint):
            continue

        matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=world_space)

        matrices[joint] = matrix

    return matrices


def set_joint_matrices_in_scene(matrices, world_space=True):
    for joint, matrix in matrices.items():
        if not cmds.objExists(joint):
            continue

        children = cmds.listRelatives(joint)

        child_matrices = [
            cmds.xform(i, query=True, matrix=True, worldSpace=True)
            for i in children
        ]

        cmds.xform(joint, matrix=matrix, worldSpace=world_space)

        for child, child_matrix in zip(children, child_matrices):
            cmds.xform(child, matrix=child_matrix, worldSpace=True)

        cmds.makeIdentity(joint, apply=True, translate=True, rotate=True)

    return True


def map_joints_to_vertex_ids(joints, mesh, threshold=0.01):
    joint_positions = [
        cmds.xform(joint, query=True, translation=True, worldSpace=True)
        for joint in joints
    ]

    vertex_ids = mhMayaUtils.get_closest_vertices(
        joint_positions, mesh, max_distance=threshold
    )

    mapped_joints = {
        joint: vertex_id for joint, vertex_id in zip(joints, vertex_ids) if vertex_id is not None
    }

    return mapped_joints
