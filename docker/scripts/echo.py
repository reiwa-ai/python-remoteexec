import sys
if __name__ == "__main__":
    line = sys.stdin.readline()
    while line and line!='end\n':
        sys.stdout.write(line)
        sys.stdout.flush()
        line = sys.stdin.readline()