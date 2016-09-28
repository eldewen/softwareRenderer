import re
import util
from datetime import datetime

def readObjFile(objFilename):
    vertices = []
    faces = []
    color = (255, 255, 255)
    print('Reading model "%s"...' % objFilename)
    with open(objFilename) as fp:
        for line in fp:
            xs = line.strip().split(' ')
            if xs[0] == 'v':
                vertices.append(util.Vertex(
                    float(xs[1]), float(xs[2]), float(xs[3]), color))
            elif xs[0] == 'f':
                faces.append(
                    tuple(int(re.sub(r'(\d+).*', r'\1', i)) for i in xs[1:]))
    print("Read %d vertices and %d faces" % (len(vertices), len(faces)))
    return vertices, faces

def writeObjFile(vertices, faces, objFilename):
    with open(objFilename, "w") as fp:
        fp.write("# Generated by DB on %s\n" % datetime.now().isoformat())
        fp.write("o %s\n" % objFilename)
        [fp.write("v %f %f %f\n" % (v.x, v.y, v.z)) for v in vertices]
        [fp.write("f %d %d %d\n" % f) for f in faces]