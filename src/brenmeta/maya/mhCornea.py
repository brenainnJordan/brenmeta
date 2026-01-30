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

"""Cornea bulge deformation utilities
"""
from maya.api import OpenMaya

from brenmeta.maya import mhMayaUtils


class CorneaDeformer(object):
    # TODO continue and test!!!
    def __init__(self):
        self.mesh = None
        self.eyeball_mesh = None
        self.eyeball_transform = None

        self.max_distance = 1000000.0

        self.mesh_offsets = None

    def initialize(self):
        mesh_points = mhMayaUtils.get_points(self.mesh)

        eyeball_mesh_dag = mhMayaUtils.parse_dag_path(self.eyeball_mesh)
        eyeball_mesh_fn = OpenMaya.MFnMesh(eyeball_mesh_dag)

        centroid = OpenMaya.MFloatPoint(
            cmds.xform(
                self.eyeball_transform, query=True, translation=True, worldSpace=True
            )
        )

        self.mesh_offsets = []

        for mesh_point in mesh_points:
            ray_vector = OpenMaya.MFloatVector(mesh_point - centroid)

            hit_result = eyeball_mesh_fn.closestIntersection(
                OpenMaya.MFloatPoint(mesh_point),
                ray_vector,
                OpenMaya.MSpace.kWorld,
                self.max_distance,
                False
            )

            if hit_result:
                self.mesh_offsets.append(hit_result[0])
            else:
                self.mesh_offsets.append(None)

        return True

    def deform(self):
        pass
