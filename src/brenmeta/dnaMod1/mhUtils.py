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
