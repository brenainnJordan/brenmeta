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

import dna
import dnacalib
import dna_viewer

def load_dna(path):
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
    reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
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


def scale_dna(reader, scale):
    scale_cmd = dnacalib.ScaleCommand(scale, [0, 0, 0])
    scale_cmd.run(reader)
    return True
