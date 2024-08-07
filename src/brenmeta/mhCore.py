import os

import dna
import dnacalib
import dna_viewer

from maya import cmds

SRC_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.split(os.path.split(SRC_DIR)[0])[0]
DATA_DIR = os.path.join(ROOT_DIR, "data")

DNA_VIEWER_DIR = os.path.dirname(os.path.dirname(dna_viewer.__file__))
DNA_DATA_DIR = os.path.join(DNA_VIEWER_DIR, "data")


class MHError(Exception):
    def __init__(self, *args, **kwargs):
        super(MHError, self).__init__(*args, **kwargs)

def load_dna(path):
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
    reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    reader.read()
    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError("Error loading DNA: {}".format(status.message))
    return reader


def save_dna(reader, path, validate=True):
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Write, dna.FileStream.OpenMode_Binary)
    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(reader)
    writer.write()

    if validate:
        if not dna.Status.isOk():
            status = dna.Status.get()
            raise RuntimeError("Error saving DNA: {}".format(status.message))

    return True

