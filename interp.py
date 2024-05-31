import sys
from time import sleep

verbose = False
NONTERMINAL = 1
TERMINAL = 2

class CompileError(BaseException):
    def __init__(self, source_path: str, ln: int, line: str, msg=None):
        self.source_path = source
        self.ln = ln
        self.line = line
        self.message = msg
    def __str__():
        return f'Error: File {self.source_path}, line {self.ln}:' \
        + f"    Invalid syntax: {self.message+': ' if self.message else ''}" \
        + f"        {self.line}"

class ExecutionInterrupt(BaseException):
    pass

def compile(source_code: str, source_path='<script>'):
    source = []
    ln = 0
    for line in source_code.splitlines():
        ln += 1
        line = line.split('~')[0]
        if not line: continue
        if ' : ' in line:
            (l_side, r_side), method = line.split(' : '), NONTERMINAL
        elif ' ; ' in line:
            (l_side, r_side), method = line.split(' ; '), TERMINAL
        else:
            CompileError(source_path, ln, line, 'No valid method provided')
        l_side, r_side = l_side.strip(), r_side.strip()
        if not l_side or not r_side:
            CompileError(source_path, ln, line, f"No {'left' if not l_side else 'right'} side provided")
        l_side, r_side = l_side.replace('#', ''), r_side.replace('#', '')
        source.append((method, l_side, r_side))
    return source

kill = False
delay = 0.0
def execute(code: list, entry: str):
    global kill
    kill = False
    loop = True
    while loop:
        for method, l_side, r_side in code:
            if kill: raise ExecutionInterrupt()
            if l_side in entry:
                sleep(delay)
                if verbose: print('--D: ', f'{l_side:>10}', '>->' if method == TERMINAL else '-->', f'{r_side:<10}', '|', f'{entry:>15}', '>->' if method == TERMINAL else '-->', end=' ')
                entry = entry.replace(l_side, r_side, 1)
                if method == TERMINAL: loop = False
                if verbose: print(entry)
                break
    return entry

def interrupt():
    global kill
    kill = True

if __name__ == '__main__':
    if '-v' in sys.argv or '--verbose' in sys.argv:
        verbose = True
        sys.argv.remove('-v' if '-v' in sys.argv else '--verbose')
    if '-d' in sys.argv or '--delay' in sys.argv:
        pos = sys.argv.index('-d' if '-d' in sys.argv else '--delay')
        delay = float(sys.argv[pos+1])
        del sys.argv[pos:pos+2]
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) < 2:
        print('Usage: alt.py [-v] [--verbose] [-h] [--help] <source.alt> [input]')
        exit()
    source_path = sys.argv[1]
    source_code = open(source_path, 'r').read()
    entry = sys.argv[2] if len(sys.argv) > 2 else input('Enter input: ')
    code = compile(source_code, source_path)
    try:
        print(('Output: ' if verbose else '') + execute(code, entry))
    except KeyboardInterrupt: pass
