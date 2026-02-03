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
from maya import cmds

from brenmeta.core import mhCore
from brenmeta.maya import mhMayaUtils
from brenmeta.maya import mhBlendshape

class CorneaDeformer(object):
    # TODO continue and test!!!
    def __init__(self):
        self.mesh = None
        self.eyeball_mesh = None
        self.eyeball_transform = None

        self.max_distance = 1000000.0

        self.mesh_offsets = None

    def project_points(self, mesh_points):
        eyeball_mesh_dag = mhMayaUtils.parse_dag_path(self.eyeball_mesh)
        eyeball_mesh_fn = OpenMaya.MFnMesh(eyeball_mesh_dag)

        centroid = OpenMaya.MFloatPoint(
            cmds.xform(
                self.eyeball_transform, query=True, translation=True, worldSpace=True
            )
        )

        ray_vectors = []
        hit_results = []

        for mesh_point in mesh_points:
            ray_vector = OpenMaya.MFloatVector(OpenMaya.MFloatPoint(mesh_point) - centroid)
            ray_vectors.append(ray_vector)

            hit_result = eyeball_mesh_fn.closestIntersection(
                OpenMaya.MFloatPoint(mesh_point),
                ray_vector,
                OpenMaya.MSpace.kWorld,
                self.max_distance,
                True
            )

            hit_results.append(hit_result)

        return ray_vectors, hit_results

    def initialize(self):
        mesh_points = mhMayaUtils.get_points(self.mesh)

        ray_vectors, hit_results = self.project_points(mesh_points)

        self.mesh_offsets = []

        for mesh_point, ray_vector, hit_result in zip(mesh_points, ray_vectors, hit_results):
            if hit_result:
                param = hit_result[1]
                offset = ray_vector.length() * param
                self.mesh_offsets.append(offset)
            else:
                self.mesh_offsets.append(None)

        # calculate an appropriate max distance based on eye bounding box
        bbox = cmds.exactWorldBoundingBox(self.eyeball_mesh)
        eyeball_width = bbox[3] - bbox[0]

        self.max_distance = eyeball_width

        return True

    def deform_mesh(self, mesh=None):
        if not self.mesh_offsets:
            raise mhCore.MHError("Deformer not initialized")

        if mesh is not None:
            # TODO check point count
            pass
        else:
            mesh = self.mesh

        mesh_points = mhMayaUtils.get_points(mesh)

        ray_vectors, hit_results = self.project_points(mesh_points)

        deformed_points = []

        for mesh_point, ray_vector, hit_result, mesh_offset in zip(
                mesh_points, ray_vectors, hit_results, self.mesh_offsets
        ):
            if hit_result and mesh_offset:
                # calculate the new vertex position
                # we need to offset our hit point by the stored vertex offset
                # along the ray vector but pointing away from the eye pivot
                # to do this we simply normalize the ray vector, multiply by -1.0,
                # multiply by the vertex offset, then add to the hit point
                hit_point = hit_result[0]
                deformed_point = hit_point + (ray_vector.normal() * -1.0 * mesh_offset)
                deformed_points.append(deformed_point)
            else:
                deformed_points.append(mesh_point)

        mhMayaUtils.set_points(mesh, deformed_points)

        return True

    def deform_target(self, bs_node, target, sculpt=True, mesh=None):
        # TODO!
        target_delta = mhBlendshape.get_target_delta(bs_node, target)
