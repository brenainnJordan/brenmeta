# brenmeta
metahuman dna modification tool

While Epic Games does provide a Maya metahuman modification tool,
it can be quite restrictive in how much you can modify.

This tool is a more of a sandbox, that allows you to modify
a metahuman face rig to a greater degree, and create more
unique and interesting characters rigs.


# dependencies

Install dependencies via pip using mayapy.exe and the included requirements.txt file

eg.

    "C:\Program Files\Autodesk\Maya2023\bin\mayapy.exe" -m pip install -r D:\Repos\brenmeta\requirements.txt

**Unreal 5.6 onwards:**

For modern versions of Unreal, please download and install the
MetaHuman for Maya plugin:

https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-for-maya


**Unreal 5.5 or older:**

If you are using dna files from an Unreal version before 5.6,
you need to download and install the MetaHuman-DNA-Calibration library
from the EpicGames github:

https://github.com/EpicGames/MetaHuman-DNA-Calibration/tree/main


# installation
Add the "src" folder to sys.path or your PYTHONPATH env variable

eg.

    import sys
    
    path = r"D:\Repos\brenmeta\src"
    
    if path not in sys.path:
            sys.path.append(path)

# using the tool
Once installed the tool can be called like this:

    import brenmeta
    gui = brenmeta.show(version=2)

Use version=2 for Unreal 5.6 onwards, or version=1 for Unreal 5.5 or older

# license
This tool is provided with a GNU license, and is free to use.
You may modify or add to the code, but you are expected to contribute back to the source (please do so in a new branch).
Closed source development of this tool is not permitted.
