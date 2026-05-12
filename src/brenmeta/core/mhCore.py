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

"""Core functionality with no dependencies on dna"""

import os
import sys
import json

import logging

from maya import cmds


def ascend_path(path, levels):
    for _ in range(levels):
        path = os.path.dirname(path)
    return path


SRC_DIR = os.path.dirname(__file__)
ROOT_DIR = ascend_path(SRC_DIR, 3)
DATA_DIR = os.path.join(ROOT_DIR, "data")


def get_basic_logger(name):
    logger = logging.getLogger(name)

    if not len(logger.handlers):
        # logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        # consoleHandler.setLevel(logging.INFO)
        logger.addHandler(handler)

        formatter = logging.Formatter('%(levelname)s: %(message)s ~ %(name)s')
        logger.handlers[0].setFormatter(formatter)

        logger.propagate = False
        logger.setLevel(logging.INFO)

    return logger


LOG = get_basic_logger(__name__)


class MHError(Exception):
    def __init__(self, *args, **kwargs):
        super(MHError, self).__init__(*args, **kwargs)


def remove_module_from_sys(module):
    """Forcefully remove module from memory and sys.path so other versions can be sourced
    """

    module_path = None

    for path in sys.path:
        if path in module.__file__:
            module_path = path
            break

    if not module_path:
        raise MHError("Failed to find module path: {}".format(module))

    LOG.warning("Removing module: {}".format(module_path))

    sys.path.remove(module_path)

    module_name = module.__name__
    del module
    del sys.modules[module_name]

    return True


def validate_arg(arg_name, arg_value, expected_type, can_be_none=False):
    if arg_value is None:
        if can_be_none:
            return True
        else:
            raise MHError("{} arg cannot be None".format(arg_name))

    if not isinstance(arg_value, expected_type):
        raise MHError("{} arg should {} not {}".format(arg_name, expected_type, arg_value))

    return True


class Pose(object):
    def __init__(self, pose_manager, name=None, index=None, shape_name=None):
        validate_arg("pose_manager", pose_manager, PoseManager)

        self.pose_manager = pose_manager
        self.index = index
        self.name = name
        self.shape_name = shape_name
        self.deltas = {}
        self.defaults = {}
        self.opposite = None  # TODO

    def __add__(self, other):
        """Returned summed Pose
        """
        summed_pose = Pose(
            self.pose_manager,
            name="{}_{}".format(self.name, other.name)
        )

        for attr, delta in self.deltas.items():
            if attr in summed_pose.deltas:
                summed_pose.deltas[attr] += delta
            else:
                summed_pose.deltas[attr] = delta

        for attr, delta in other.deltas.items():
            if attr in summed_pose.deltas:
                summed_pose.deltas[attr] += delta
            else:
                summed_pose.deltas[attr] = delta

        return summed_pose

    def __repr__(self):
        return "{}({}: {})".format(self.__class__.__name__, self.index, self.name)

    def get_display_name(self, index=True, blendshape=True):
        display_name = ""

        if index:
            display_name += "{}: ".format(self.index)

        if self.name:
            display_name += "{}".format(self.name)

        if blendshape:
            display_name += " ({})".format(self.shape_name)

        return display_name

    def get_default(self, attr):
        if attr in self.pose_manager.attr_defaults:
            default = self.pose_manager.attr_defaults[attr]
        else:
            LOG.warning("attr not in defaults: {} ({})".format(attr, self))
            default = 0.0

        return default

    def get_values(self, absolute=True, blend=1.0):
        if absolute:
            if not self.pose_manager:
                raise MHError("Cannot get absolute values without pose manager")

            values = {}

            for attr, delta in self.deltas.items():
                default = self.get_default(attr)
                delta *= blend
                values[attr] = default + delta

            return values
        else:
            return self.deltas

    def pose_joints(self, blend=1.0):
        for attr, value in self.get_values(absolute=True, blend=blend).items():
            if not cmds.objExists(attr):
                continue

            cmds.setAttr(attr, value)

        return True

    def activate_targets(self, blendshape_nodes, blend=1.0):
        if not self.shape_name:
            return False

        for blendshape_node in blendshape_nodes:
            if not cmds.objExists(blendshape_node):
                continue

            if not cmds.attributeQuery(self.shape_name, node=blendshape_node, exists=True):
                continue

            cmds.setAttr("{}.{}".format(blendshape_node, self.shape_name), blend)

        return True

    def update_from_scene(self):
        for attr, old_value in self.deltas.items():
            default = self.get_default(attr)
            value = cmds.getAttr(attr)
            self.deltas[attr] = value - default

        return True

    def scale_deltas(self, value, attrs=None, joints=None):
        # default to just scaling translation
        if attrs is None:
            attrs = ["tx", "ty", "tz"]

        for pose_attr in self.deltas.keys():
            joint, attr = pose_attr.split(".")

            if attr not in attrs:
                continue

            if joints:
                if joint not in joints:
                    continue

            self.deltas[pose_attr] *= value

        return True

    def affects_joint(self, joint):
        for attr, value in self.deltas.items():
            if value == 0.0:
                continue

            attr_joint, attr = attr.split(".")

            if attr_joint == joint:
                return True

        return False

    def affects_joints(self, joints):
        for attr in self.deltas.keys():
            attr_joint, attr = attr.split(".")

            if attr_joint in joints:
                return True

        return False

    def serialize(self):
        data = {
            "index": self.index,
            "name": self.name,
            "shape_name": self.shape_name,
            "deltas": self.deltas,
        }

        if self.opposite:
            data["opposite"] = self.opposite.index
        else:
            data["opposite"] = None

        return data

    def deserialize(self, data):
        self.index = data["index"]
        self.name = data["name"]
        self.shape_name = data["shape_name"]
        self.deltas = data["deltas"]

        if data["opposite"] is not None:
            self.opposite = self.pose_manager.poses[data["opposite"]]

        return True


class ComboPose(object):
    def __init__(self, pose_manager):
        super(ComboPose, self).__init__()

        validate_arg("pose_manager", pose_manager, PoseManager)

        self.pose_manager = pose_manager
        self.pose = None
        self.input_poses = []
        self.input_weights = []  # TODO deprecate?
        self.input_combos = []

    def __repr__(self):
        return "{}({}: {}) <- [{}]".format(
            self.__class__.__name__, self.pose.index, self.pose.name,
            [pose.name or pose.index for pose in self.input_poses]
        )

    def get_values(self, summed=True, absolute=True, blend=1.0):
        """
        Note the input weight is not used here (nor in the rig logic)
        it actually seems to cause issues
        """
        if not summed:
            return self.pose.get_values(absolute=absolute, blend=blend)

        summed_deltas = dict(self.pose.deltas)

        for pose in self.get_all_input_poses(include_combos=True):
            for attr, delta in pose.deltas.items():
                if attr in summed_deltas:
                    summed_deltas[attr] += delta
                else:
                    summed_deltas[attr] = delta

        if absolute:
            if not self.pose_manager:
                raise MHError("Cannot get absolute values without pose manager: {}".format(self))

            values = {}

            for attr, value in summed_deltas.items():
                # if attr not in self.pose_manager.attr_defaults:
                #     raise MHError("attr not in defaults: {}".format(attr))

                if attr in self.pose_manager.attr_defaults:
                    default = self.pose_manager.attr_defaults[attr]
                else:
                    LOG.warning("attr not in defaults: {} ({})".format(attr, self))
                    default = 0.0

                values[attr] = default + (value * blend)

            return values

        else:
            return summed_deltas

    def pose_joints(self, summed=True, blend=1.0):
        for attr, value in self.get_values(summed=summed, absolute=True, blend=blend).items():
            if not cmds.objExists(attr):
                continue

            cmds.setAttr(attr, value)

        return True

    def activate_targets(self, blendshape_nodes, blend=1.0):
        poses = self.get_all_input_poses(include_combos=True)

        for pose in poses:
            if isinstance(pose, ComboPose):
                pose.pose.activate_targets(blendshape_nodes, blend=blend)
            else:
                pose.activate_targets(blendshape_nodes, blend=blend)

        return True

    def get_all_input_poses(self, include_combos=False):
        poses = set(self.input_poses)

        for input_combo_pose in self.input_combos:
            if include_combos:
                poses.add(input_combo_pose.pose)

            poses.update(input_combo_pose.get_all_input_poses())

        # sort by index
        poses = sorted(poses, key=lambda p: p.index)

        return poses

    def update_name(self, override=True):
        if self.pose.name and not override:
            raise MHError("ComboPose is already named: {}".format(self))

        sides = set([])

        name_tokens = []

        for pose in self.get_all_input_poses():
            if not pose.name:
                LOG.info("unable to update Combo name: {}".format(self))
                return self.pose.name

            if pose.name[-1] in "LR":
                sides.add(pose.name[-1])
                pose_name = pose.name[:-1]
            else:
                pose_name = pose.name

            if pose_name not in name_tokens:
                name_tokens.append(pose_name)

        self.pose.name = "_".join(name_tokens)

        if sides:
            self.pose.name = "{}_{}".format(self.pose.name, "".join(sorted(sides)))

        return self.pose.name

    def affects_joint(self, joints):
        for pose in self.get_all_input_poses():
            if pose.affects_joint(joints):
                return True

        return False

    def affects_joints(self, joints):
        for pose in self.get_all_input_poses():
            if pose.affects_joints(joints):
                return True

        return False

    def serialize(self):
        data = {
            "pose": None,
            "input_poses": None,
            "input_weights": None,
            "input_combos": None
        }

        if self.pose:
            data["pose"] = self.pose.serialize()

        if self.input_poses:
            data["input_poses"] = [pose.index for pose in self.input_poses]

        if self.input_weights:
            data["input_weights"] = self.input_weights

        if self.input_combos:
            data["input_combos"] = [combo.pose.index for combo in self.input_combos]

        return data

    def deserialize(self, data):  # , pose_manager):
        # if data["index"]:
        #     if data["index"] >= len(pose_manager.poses):
        #         raise MHError("combo pose index out of range: {}".format(data["index"]))
        #
        #     self.pose = pose_manager.poses[data["index"]]

        # self.pose_manager = pose_manager

        if data["pose"]:
            self.pose = Pose(self.pose_manager)
            self.pose.deserialize(data["pose"])

        if data["input_poses"]:
            self.input_poses = []

            for pose_index in data["input_poses"]:
                if pose_index >= len(self.pose_manager.poses):
                    raise MHError("input pose index out of range: {}".format(pose_index))

                self.input_poses.append(self.pose_manager.poses[pose_index])

        if data["input_weights"]:
            self.input_weights = data["input_weights"]

        if data["input_combos"]:
            self.input_combos = []

            for pose_index in data["input_combos"]:
                # TODO check is actually combo?
                self.input_combos.append(self.pose_manager.poses[pose_index])

                # if pose_index not in pose_manager.combo_poses:
                #     raise MHError("input combo index not found: {}".format(pose_index))
                #
                # self.input_combos.append(pose_manager.combo_poses[pose_index])

        return True


class PoseManager(object):

    def __init__(self):
        super(PoseManager, self).__init__()

        self.attrs = []
        self.attr_defaults = {}
        self._poses = []
        # self.combo_poses = {}
        self.blendshape_nodes = []

    # @property
    # def core_poses(self):
    #     if not self.poses:
    #         return None
    #
    #     return [pose for i, pose in enumerate(self.poses) if i not in self.combo_poses]

    # @property
    # def sorted_combo_poses(self):
    #     return [self.combo_poses[i] for i in sorted(self.combo_poses.keys())]

    @property
    def poses(self):
        return self._poses

    def set_poses(self, poses):
        self._poses = poses

        for pose in poses:
            pose.pose_manager = self

    @property
    def core_poses(self):
        return [pose for pose in self.poses if isinstance(pose, Pose)]

    @property
    def combo_poses(self):
        return [pose for pose in self.poses if isinstance(pose, ComboPose)]

    def reset(self):
        self.attrs = []
        self.attr_defaults = {}
        self._poses = []
        self.blendshape_nodes = []

    def serialize(self):
        data = {
            "attrs": self.attrs,
            "attr_defaults": self.attr_defaults,
            "poses": None,
            # "combo_poses": None,
            "pose_count": 0,
            # "combo_pose_count": 0,
            "combo_indices": None,
            "blendshape_nodes": self.blendshape_nodes,
        }

        if self.poses:
            data["poses"] = [pose.serialize() for pose in self.poses]
            data["pose_count"] = len(self.poses)
            data["combo_indices"] = [i for i, pose in enumerate(self.poses) if isinstance(pose, ComboPose)]

        # if self.combo_poses:
        #     data["combo_poses"] = {i: combo.serialize() for i, combo in self.combo_poses.items()}
        #     data["combo_pose_count"] = len(self.combo_poses)

        return data

    def deserialize(self, data):
        # instance objects
        if data["poses"]:
            self._poses = [
                ComboPose(self) if i in data["combo_indices"] else Pose(self) for i in range(data["pose_count"])
            ]

            # deserialize after objects are instanced to ensure references are set correctly
            for i, pose_data in enumerate(data["poses"]):
                self._poses[i].deserialize(pose_data)

        # if data["combo_poses"]:
        #     for i, combo_data in data["combo_poses"].items():
        #         self.combo_poses[i].deserialize(combo_data)

        return True

    def add_additional_poses(self, pose_names, pose_deltas=None):
        pose_count = len(self.poses)

        new_poses = []

        for i, pose_name in enumerate(pose_names):
            pose = Pose(
                self,
                name=pose_name,
                index=pose_count + i,
            )

            # pose.defaults = self.attr_defaults

            new_poses.append(pose)
            self.poses.append(pose)

            if pose_deltas:
                if pose_name in pose_deltas:
                    pose.deltas = pose_deltas[pose_name]

        return new_poses

    def add_additional_combo_poses(self, additional_combos):
        """Create ComboPose for each additional combo and map input poses
        """
        pose_dict = {
            pose.pose.name if isinstance(pose, ComboPose) else pose.name: pose for pose in self.poses
        }

        pose_count = len(self.poses)

        new_combo_poses = []

        for i, pose_names in enumerate(additional_combos):
            combo = ComboPose(self)

            combo.pose = Pose(
                self,
                name="_".join(pose_names),
                index=pose_count + i,
            )

            # combo.pose.defaults = self.attr_defaults

            combo.input_poses = [pose_dict[pose_name] for pose_name in pose_names]
            combo.input_weights = [1.0] * len(pose_names)

            combo.update_name(override=True)

            if combo.pose.name in pose_dict:
                LOG.info("existing combo found, skipping: {}".format(combo.pose.name))
                continue

            # self.combo_poses[combo.pose.index] = combo
            # self.poses.append(combo.pose)
            self.poses.append(combo)
            new_combo_poses.append(combo)
            pose_dict[combo.pose.name] = combo.pose

        return new_combo_poses

    def add_combo_pose_permutations(self, pose_names, permutation_count):
        # TODO
        pass

    def update_input_combo_poses(self):
        """add input combos for 3+ way combos
        """
        for combo_pose in self.combo_poses:  # .values():
            if len(combo_pose.input_poses) < 3:
                continue

            for input_combo_pose in self.combo_poses:  # .values():
                if input_combo_pose is combo_pose:
                    continue

                if input_combo_pose in combo_pose.input_combos:
                    continue

                if len(input_combo_pose.input_poses) >= len(combo_pose.input_poses):
                    continue

                # check if all input_combo_pose input poses are contained
                # within the input combo poses for this combo
                if all([
                    pose in combo_pose.input_poses for pose in input_combo_pose.input_poses
                ]):
                    combo_pose.input_combos.append(input_combo_pose)

        return True

    def initialize_shape_names(self):
        """Add shape name to poses without shape names and ensure they are all unique
        """
        target_names = []

        for pose in self.poses:
            if isinstance(pose, ComboPose):
                pose = pose.pose

            if not pose.name:
                continue

            if not pose.shape_name:
                # use pose name
                pose.shape_name = pose.name

            # ensure shape name is unique
            duplicate_index = 1

            while pose.shape_name in target_names:
                pose.shape_name = "{}_{}".format(pose.name, duplicate_index)
                duplicate_index += 1

            target_names.append(pose.shape_name)

        return True

    def find_pose(self, pose_name):
        for pose in self.poses:
            if isinstance(pose, Pose):
                if pose.name == pose_name:
                    return pose
            elif isinstance(pose, ComboPose):
                if pose.pose.name == pose_name:
                    return pose

        return None

    def find_opposite(self, pose, find, replace, ends_with=True):
        if isinstance(pose, ComboPose):
            pose = pose.pose

        if ends_with:
            if not pose.name.endswith(find):
                raise MHError("Pose does not end with '{}': {}".format(find, pose.name))

            opposite_name = pose.name[:-1] + replace
        else:
            opposite_name = pose.name.replace(find, replace)

        opposite = self.find_pose(opposite_name)

        if not opposite:
            return None

        if isinstance(opposite, ComboPose):
            pose.opposite = opposite.pose
        else:
            pose.opposite = opposite

        return pose.opposite

    def find_opposites(self, search_str_a, search_str_b, ends_with=True):
        """
        TODO dialog
            enum for startswith, endswith, contains

        """
        for find, replace in [(search_str_a, search_str_b), (search_str_b, search_str_a)]:
            for pose in self.poses:
                if isinstance(pose, ComboPose):
                    pose = pose.pose

                if not pose.name:
                    continue
                if ends_with:
                    if not pose.name.endswith(find):
                        continue
                elif find not in pose.name:
                    continue

                opposite = self.find_opposite(pose, find, replace, ends_with=ends_with)

        return True

    def reset_joints(self):
        for attr, value in self.attr_defaults.items():
            if not cmds.objExists(attr):
                continue

            if value is None:
                continue

            try:
                cmds.setAttr(attr, value)
            except RuntimeError as err:
                LOG.warning("failed to reset joint attr: {}".format(attr))
                continue

        return True


class PoseViewSettings(object):
    ATTRS = ["show_index", "show_pose", "show_shape", "show_opposite"]

    def __init__(self):
        self.show_index = True
        self.show_pose = True
        self.show_shape = True
        self.show_opposite = True

    def serialize(self):
        data = {
            attr: getattr(self, attr) for attr in self.ATTRS
        }

        return data

    def deserialize(self, data):
        for attr in self.ATTRS:
            if attr not in data:
                continue

            setattr(self, attr, data[attr])


class Project(object):
    def __init__(self, dna_assets_path):
        self.current_file = None

        self.dna_assets_path = None
        self.input_dna_path = None
        self.output_dna_path = None
        self.bake_config_path = None

        # poses
        self.pose_manager = PoseManager()

        self.pose_config_view_settings = PoseViewSettings()
        self.core_pose_view_settings = PoseViewSettings()
        self.combo_pose_view_settings = PoseViewSettings()

        self.core_pose_view_settings.show_opposite = False
        self.core_pose_view_settings.show_shape = False

        self.combo_pose_view_settings.show_opposite = False
        self.combo_pose_view_settings.show_shape = False

        self.reset(dna_assets_path)

    def get_path(self, asset):
        dna_paths = {
            "Input Dna": self.input_dna_path,
            "Output Dna": self.output_dna_path,
        }

        if asset in dna_paths:
            return dna_paths[asset]

        return None

    def reset(self, dna_assets_path):
        self.current_file = None

        self.pose_manager.reset()

        self.dna_assets_path = dna_assets_path
        self.input_dna_path = None
        self.output_dna_path = None
        self.bake_config_path = os.path.join(DATA_DIR, "configs", "bake_config.json")

    def serialize(self):
        data = {
            "dna_assets_path": self.dna_assets_path,
            "input_dna_path": self.input_dna_path,
            "output_dna_path": self.output_dna_path,
            "bake_config_path": self.bake_config_path,
            # pose editor
            "pose_manager": self.pose_manager.serialize(),
            "pose_config_view_settings": self.pose_config_view_settings.serialize(),
            "core_pose_view_settings": self.core_pose_view_settings.serialize(),
            "combo_pose_view_settings": self.combo_pose_view_settings.serialize(),
        }

        return data

    def write(self, filepath):
        data = self.serialize()

        json_data = json.dumps(
            data, sort_keys=True, indent=4, separators=(',', ': ')
        )

        with open(filepath, "w") as f:
            f.write(json_data)

        return True

    def read(self, filepath):
        if not os.path.exists(filepath):
            raise MHError("File not found: {}".format(filepath))

        with open(filepath, 'r') as f:
            data = json.load(f)

        self.dna_assets_path = data["dna_assets_path"]
        self.input_dna_path = data["input_dna_path"]
        self.output_dna_path = data["output_dna_path"]
        self.bake_config_path = data["bake_config_path"]

        self.pose_config_view_settings.deserialize(data["pose_config_view_settings"])
        self.core_pose_view_settings.deserialize(data["core_pose_view_settings"])
        self.combo_pose_view_settings.deserialize(data["combo_pose_view_settings"])

        self.current_file = filepath

        self.pose_manager.reset()

        if "pose_manager" in data:
            self.pose_manager.deserialize(data["pose_manager"])

        return True
