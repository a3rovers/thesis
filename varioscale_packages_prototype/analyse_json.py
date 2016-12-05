import glob
import json

for filenm in glob.glob("/tmp/index.html*"):

    # parse file
    fh = open(filenm)
    all = fh.read()
    d = json.loads(all)

    print filenm, len(all)    
    # find position of keys in the file and total size of the file
    pos = []
    for key in d.keys():
        pos.append((all.find(key), key))
    pos.append((len(all), "EOF"))
    pos.sort()
    
    # make an estimate on how many bytes are spent on which item
    sizes = {}
    for one, two in zip(pos[:-1], pos[1:]):
        sizes[one[1]] = two[0] - one[0]
    
    # estimate (percentage) on how much space is taken inside file for what
    for key in sizes:
        print key, round(float(sizes[key]) / len(all) * 100, 4)
