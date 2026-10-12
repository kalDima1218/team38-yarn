#!/usr/bin/env python3
import sys
from itertools import groupby
rows=(line.rstrip('\n').split('\t',1) for line in sys.stdin)
for word,group in groupby(rows,key=lambda row:row[0]):
    print(f'{word}\t{sum(int(row[1]) for row in group)}')
