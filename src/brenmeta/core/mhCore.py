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
from typing import Any

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


