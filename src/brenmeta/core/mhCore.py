import os
import sys

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


def validate_arg(arg_name, arg_value, expected_type):
    if not isinstance(arg_value, expected_type):
        raise MHError("{} arg should {} not {}".format(arg_name, expected_type, arg_value))
    return True


class Pose(object):
    def __init__(self, name=None, index=None, shape_name=None):
        self.index = index
        self.name = name
        self.shape_name = shape_name
        self.deltas = {}
        self.defaults = {}
        self.opposite = None  # TODO

    def __add__(self, other):
        """Returned summed Pose
        """
        summed_pose = Pose(name="{}_{}".format(self.name, other.name))

        summed_pose.defaults = self.defaults
        summed_pose.defaults.update(other.defaults)

        for attr, delta in self.deltas.items():
            if attr in other.deltas:
                summed_pose.deltas[attr] = delta + other.deltas[attr]
            else:
                summed_pose.deltas[attr] = delta

        for attr, delta in other.deltas.items():
            if attr in self.deltas:
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

    def get_values(self, absolute=True, blend=1.0):
        if absolute:
            values = {}

            for attr, delta in self.deltas.items():
                delta *= blend
                values[attr] = self.defaults[attr] + delta

            return values
        else:
            return self.deltas

    def pose_joints(self, blend=1.0):
        for attr, value in self.get_values(absolute=True, blend=blend).items():
            cmds.setAttr(attr, value)

        return True

    def reset_joints(self):
        for attr, value in self.defaults.items():
            cmds.setAttr(attr, value)

        return True

    def update_from_scene(self):
        for attr, default in self.defaults.items():
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


class PSDPose(object):
    def __init__(self):
        super(PSDPose, self).__init__()
        self.pose = None
        self.input_poses = []
        self.input_weights = []
        self.input_psd_poses = []
        self.opposite = None  # TODO

    def __repr__(self):
        return "{}({}: {}) <- [{}]".format(
            self.__class__.__name__, self.pose.index, self.pose.name,
            [pose.name for pose in self.input_poses]
        )

    def get_defaults(self):
        defaults = dict(self.pose.defaults)

        for input_pose in self.input_poses:
            for attr, default in input_pose.defaults.items():
                if attr not in defaults:
                    defaults[attr] = default

        return defaults

    def get_values(self, summed=True, absolute=True, blend=1.0):
        """
        Note the input weight is not used here (nor in the rig logic)
        it actually seems to cause issues
        """
        if not summed:
            return self.pose.get_values(absolute=absolute, blend=blend)

        summed_deltas = dict(self.pose.deltas)
        defaults = self.get_defaults()

        for input_pose in self.input_poses:
            for attr, delta in input_pose.deltas.items():
                if attr in summed_deltas:
                    summed_deltas[attr] += delta
                else:
                    summed_deltas[attr] = delta

        for input_psd_pose in self.input_psd_poses:
            for attr, delta in input_psd_pose.pose.deltas.items():
                if attr in summed_deltas:
                    summed_deltas[attr] += delta
                else:
                    summed_deltas[attr] = delta

        if absolute:
            values = {}

            for attr, default in defaults.items():
                if attr not in summed_deltas:
                    continue

                delta = summed_deltas[attr] * blend
                values[attr] = default + delta

            return values

        else:
            return summed_deltas

    def pose_joints(self, summed=True, blend=1.0):
        for attr, value in self.get_values(summed=summed, absolute=True, blend=blend).items():
            cmds.setAttr(attr, value)

        return True

    def reset_joints(self):
        for attr, value in self.get_defaults().items():
            cmds.setAttr(attr, value)

        return True

    def get_all_input_poses(self):
        poses = set(self.input_poses)

        for input_psd_pose in self.input_psd_poses:
            poses.update(input_psd_pose.get_all_input_poses())

        # sort by index
        poses = sorted(poses, key=lambda p: p.index)

        return poses

    def update_name(self, override=True):
        if self.pose.name and not override:
            raise MHError("PSDPose is already named: {}".format(self))

        sides = set([])

        name_tokens = []

        for pose in self.get_all_input_poses():
            if not pose.name:
                continue

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
