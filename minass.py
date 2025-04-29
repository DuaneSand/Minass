# A simple assembler for one DIY 8-bit CPU, in Python3
# (c) 2025 Duane Sand

# Functionally equivalent to Carsten Herting's (SLU4) 
#   original simple Python assembler for his Minimal 8-bit machines.
# This rewrite will be easier to adapt to various 16-bit machines.

# Changes from Herting's input language:
#   Labels must start in column 1
#   At most one cpu instruction per line
#   Name spellings are limited to usual: alpha alphanum_*
#   Hex consts are lowercase only
#   Input file passed in via stdin using shell's <filename option

import sys

opCodes = { 'NOP':0,  'BNK':1,  'OUT':2,  'CLC':3,  'SEC':4,  'LSL':5,  'ROL':6,  'LSR':7,
            'ROR':8,  'ASR':9,  'INP':10, 'NEG':11, 'INC':12, 'DEC':13, 'LDI':14, 'ADI':15,
            'SBI':16, 'CPI':17, 'ACI':18, 'SCI':19, 'JPA':20, 'LDA':21, 'STA':22, 'ADA':23,
            'SBA':24, 'CPA':25, 'ACA':26, 'SCA':27, 'JPR':28, 'LDR':29, 'STR':30, 'ADR':31,
            'SBR':32, 'CPR':33, 'ACR':34, 'SCR':35, 'CLB':36, 'NEB':37, 'INB':38, 'DEB':39,
            'ADB':40, 'SBB':41, 'ACB':42, 'SCB':43, 'CLW':44, 'NEW':45, 'INW':46, 'DEW':47,
            'ADW':48, 'SBW':49, 'ACW':50, 'SCW':51, 'LDS':52, 'STS':53, 'PHS':54, 'PLS':55,
            'JPS':56, 'RTS':57, 'BNE':58, 'BEQ':59, 'BCC':60, 'BCS':61, 'BPL':62, 'BMI':63  }

hexdigits = '0123456789abcdef'

source_lines = []  # list of source line strings
labels = {}        # map of known labels to their resolved values
codemem = {}       # nonblank memory cells in final program, indexed by runtime address
code_addr = 0      # current runtime address of next empty cell
pass2 = False      # differences between pass1 and pass2 processing

lineno = 0   
line = '\n'  # current source line with trailing newline, unmodified
scan = line  # remainder of current source line with trailing newline

def setups():
   f_in = sys.stdin
   while True:
      line = f_in.readline()
      if not line: break
      source_lines.append(line)

def error(msg):
   print ('Error! ' + msg)
   print ('  in line %i  "%s"' % (lineno, line[:-1]))
   print ('  at "%s"' % scan[:10])
   #raise ValueError  ###
   exit(1)   # abort the assembly run

def scan_num():
   global scan
   i = 0; minlth = 1; longhex = False
   if scan[:2] == '0x':
      i = 2; minlth = 3
      while scan[i] in hexdigits: i += 1
      longhex = i > 4
   else:
      while scan[i].isdigit(): i += 1
   if i < minlth:
      error('Expected integer') 
   val = int(scan[:i], 0)
   if val > 0xffff:
      error('Integer out of range')
   scan = scan[i:]
   return val, longhex

def scan_name():
   global scan
   i = 0
   if not scan[i].isalpha():
      error('Expected name')
   while scan[i].isalnum() or scan[i] == '_':
      i += 1
   name = scan[:i]
   scan = scan[i:]
   return name

def emit(cellval):
   global code_addr
   if pass2:
      if cellval < 0 or cellval > 0xff:
         error('Oops, non-byte value %x didnt fit at loc %04x' % (cellval, code_addr))
      codemem[code_addr] = cellval
   code_addr += 1

def scan_quoted_string():
   global scan
   quoter = scan[0]
   i = 1 
   while not (scan[i] == quoter or scan[i] == '\n'):
      emit(ord(scan[i]))
      i += 1
   if scan[i] != quoter:
      error('Unterminated quoted string')
   i += 1   # skip final quote
   scan = scan[i:]
   cells = i-2
   return cells

def op_argument():
   global scan
   halfer = scan[0]
   if halfer == '<' or halfer == '>': scan = scan[1:]

   if scan[0].isalpha():
      name = scan_name()
      val = 0
      if pass2:
         if name not in labels:
            error ('Unknown name %s, no label' % name)
         val = labels[name]
   else:
      val,longhex = scan_num()
      if val <= 0xff and not longhex: halfer = '<'

   operator = scan[0]
   if operator == '+' or operator == '-':      
      scan = scan[1:]
      val2,longhex = scan_num()
      if operator == '+':
         val += val2
      else: 
         val -= val2

   if halfer == '<':
      emit(val & 0xff)
   elif halfer == '>':
      emit(val >> 8  )
   else:
      emit(val & 0xff)    # little-endian machine
      emit(val >> 8  )

def skip_whitespace():
   # also skips comment field if any
   global scan
   scan = scan.lstrip()  # oops, may discard final newline
   if (not scan) or (scan[0] == ';') : scan = '\n'

def expect_eol():
   skip_whitespace()
   if scan[0] != '\n':
      error('Expected comment or end of line')     

def scan_label():
   global scan
   name = scan_name()
   if scan[0] != ':':
      error('Expected : after label')
   scan = scan[1:]
   if pass2:
      if labels[name] != code_addr:
         error('Oops, pass2 has different addresses')
   else:
      if name in labels:
         error('duplicate definition of label ' + name)
      labels[name] = code_addr

def org_directive():
   global scan, code_addr
   scan = scan[4:]
   skip_whitespace()
   code_addr,longhex = scan_num()

def instr_line():
   name = scan_name()
   if name not in opCodes:
      error('Expected opcode')
   opval = opCodes[name]
   emit(opval)
   skip_whitespace()
   if scan[0] != '\n':
      op_argument()

def inlined_consts():
   global scan
   while scan[0] != '\n':
      if scan[0] == "'":
         scan_quoted_string()
      else:
         val,longhex = scan_num()
         if longhex:
            emit(val >> 8  )     # little-endian machine
            emit(val & 0xff)
         else:
            emit(val)
      if scan[0] == ',': scan = scan[1:]
      skip_whitespace()

def passover(is_pass2):
   # Parse the entire input file of assembler source code,
   #   working out the translation of each line to machine code.
   # This is here done twice, in two very similar sequential passes.
   # The final machine code depends on the address values of branch-target labels,
   #   but addresses aren't known for forward-ref branches during the first pass.
   # The first pass's official job is just to work out the addresses for all labels.
   # This depends on the number and sizes of instructions and constants in between.
   # The simplest way to work that out, is to do most all the work of translating
   #   instructions from source form to binary.  But that tentative emitted code is thrown away.
   # The second pass again parses everything from source again, but this time has
   #   correct address values for all labels, and the emitted code is final and retained.

   # Historically, many memory-constrained assemblers did all work in a first pass,
   #   and then fixed up incomplete branch ops in a second half-pass.  
   #   That method is harder to apply to arbitrary target machines,
   #   and is unneeded now with large fast host machines.

   global lineno, line, scan, code_addr, pass2
   pass2 = is_pass2
   code_addr = 0   # default, usually overridden by an initial #org directive
   lineno = 0
   for line in source_lines:
      lineno += 1
      scan = line
      if scan[0].isalpha():
         scan_label()
      skip_whitespace()
      if scan[0] == '\n':
         pass
      elif scan.startswith('#org'):
         org_directive()
      elif scan[0].isalpha():
         instr_line()
      else:
         inlined_consts()
      expect_eol()

def codedump(locvalpairs):
   next = -2
   s = ''
   for pair in locvalpairs:
      addr,cellval = pair
      if len(s) > 16*3 or addr != next: print(s); s = ':'
      if addr != next:
         print ('%04x' % addr)
         next = addr
      s += '%02x ' % cellval
      next += 1
   print (s)
   print ()
   
def labeldump():
   namelocpairs = list(labels.items())
   namelocpairs.sort()
   for name,loc in namelocpairs:
      print ('%04x: %s' % (loc, name))
   print ()

def finals():
   locvalpairs = list(codemem.items())
   locvalpairs.sort()
   codedump(locvalpairs)
   labeldump()
      
# Main:
setups()
passover(False)  # Pass 1: discover label values
passover(True)   # Pass 2: translate and emit final instructions
finals()

# End!