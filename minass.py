# MINASS: A Minimal Assembler in Python3 for Ken Boak's new 2025 Suite16 CPU
# (c) 2025 Duane Sand, MIT license applies

# Input file passed in using shell's <filename option

import sys

hexdigits = '0123456789abcdefABCDEF'

opTable = {}       # map of opcode names to (format, basebits) pairs
source_lines = []  # list of source line strings
labels = {}        # map of known labels to their resolved values
codemem = {}       # nonblank 16-bit memory cells in final program, indexed by runtime address
code_addr = 0      # current runtime address of next empty cell
current_label = '' # label on current line, if any
pass2 = False      # differences between pass1 and pass2 processing
opshift = 0        # used only during setup

lineno = 0   
line = '\n'  # current source line with trailing newline, unmodified
scan = line  # remainder of current source line with trailing newline

def stuff_ops(format, oplist):
  for i in range(0, len(oplist), 2):
     opname = oplist[i]; opnum = oplist[i+1]
     assert opname not in opTable
     opTable[opname] = (format, opnum << opshift)

# Instruction formats give the bit-packing of instruction words
#   and the allowed source forms of expected instruction operands
#   for now, use arbitary names for the formats  
f1 = 1  # primary opcode,   mem/lit/Rn@+disp arg, possibly two iwords
f2 = 2  # secondary opcode, mem/Rn arg, single iword
f3 = 3  # secondary opcode, no  arg, single iword
f4 = 4  # secondary opcode, mem arg, two iwords
f5 = 5  # pseudo instructions

def build_optable():
  global opshift
  opshift = 12  # instructions decoded by 4-bit primary opcode field
  stuff_ops(f1, (           'SET', 1,  'st',  2,  'ST@', 3,  
                 'PUSH',4,  'INV', 5,  'DEC', 6,  'INC', 7,
                 'ld' , 8,  'LD@', 9,  'POP',10,  'ADD',11,
                 'SUB',12,  'AND',13,  'OR' ,14,  'XOR',15))

  opshift = 8  # instructions decoded by secondary 4-bit opcode field, primary == 0
  stuff_ops(f2, ('BRA', 0,  'BGT', 1,  'BLT', 2,  'BGE', 3,
                 'BLE', 4,  'BNE', 5,  'BEQ', 6,
                                       'ADI',10,  'SBI',11))
  stuff_ops(f3, (           'RET', 9,  
                 'OUT',12,  'IN', 13,  'JMP@',14, 'NOP',15)) 
  stuff_ops(f4, (                                 'JMP', 7,
                 'CALL',8))
  stuff_ops(f4, ('call',8))  # lowercase alias just for this one opcode
  # special macros with another arg naming explicit R0, and optional @ on other arg rather than on opcode
  stuff_ops(f5, ('LD',  0,  'ST',  0))
  
def predefined_names():
  # Registers R0..R15 can be accessed as memory locations
  for i in range(16):  labels['R%i' % i] = i
  #labels['ACC'] = 0  # ie R0  

def setups():
   while True:
      line = sys.stdin.readline()
      if not line: break
      source_lines.append(line)
   build_optable()
   predefined_names()

def error(msg):
   print ('Error! ' + msg)
   print ('  in line %i  "%s"' % (lineno, line[:-1]))
   print ('  at "%s"' % scan[:10])
   #raise ValueError  ###  to diagnose bugs in assembler
   exit(1)   # abort the assembly run
 
def scan_num():
   global scan
   #print ('scan_num ' + repr(scan[:20]))  ###
   i = 0
   if scan[0] == '$':
      i = 1
      while scan[i] in hexdigits: i += 1
      if i < 2 : error('Expected hex integer')
      val = int(scan[1:i], 16)      
   else:
      while scan[i].isdigit(): i += 1
      if i == 0:  error('Expected number')
      val = int(scan[:i]) 
   if val > 0xffff:
      error('Integer out of range')
   scan = scan[i:]
   return val

def scan_name(allow_at=False):
   global scan
   i = 0
   if not (scan[i].isalpha() or scan[i] == '_'):
      error('Expected name')
   while scan[i].isalnum() or scan[i] == '_' or (allow_at and scan[i] == '@'):
      i += 1
   name = scan[:i]
   scan = scan[i:]
   return name

def emit(cellval):
   global code_addr
   if pass2:
      if (cellval & 0xffff) != cellval:
         error('Value %x didnt fit into 16 bits at loc %04x' % (cellval, code_addr))
      codemem[code_addr] = cellval
   code_addr += 1

def emit448(basebits, rn, val):
    emit( basebits | (rn << 8) | (val & 0xff) )

def scan_quoted_string():
   global scan
   quoter = scan[0]
   i = 1 
   while not (scan[i] == quoter or scan[i] == '\n'):
      emit(ord(scan[i]))  # one char per word
      i += 1
   if scan[i] != quoter:
      error('Unterminated quoted string')
   i += 1   # skip final quote
   scan = scan[i:]
   cells = i-2
   return cells

def op_argument():
   global scan
   if scan[0].isalpha():
      name = scan_name()
      val = 0
      if pass2:
         if name not in labels:
            error ('Unknown name %s, no label' % name)
         val = labels[name]
   else:
      val = scan_num()

   operator = scan[0]
   if operator == '+' or operator == '-':      
      scan = scan[1:]
      val2 = scan_num()
      if operator == '+':
         val += val2
      else: 
         val -= val2

   emit(val)

def skip_whitespace():
   # also skips comment field if any
   global scan
   scan = scan.lstrip()  # oops, may discard final newline
   if (not scan) or (scan[0] == ';') : scan = '\n'

def comma():
   global scan
   if scan[0] != ',':  error('Expect comma')
   scan = scan[1:]
   skip_whitespace()

def atsign():
   global scan
   foundit = scan[0] == '@'
   if foundit:  scan = scan[1:]
   return foundit

def expect_eol():
   skip_whitespace()
   if scan[0] != '\n':
      error('Expected comment or end of line')     

def scan_label():
   global scan, current_label
   name = scan_name()
   current_label = name
   if scan[0] == ':':  scan = scan[1:]  # colon is optional
   if pass2:
      pass  # this check always fails on .EQU statement
      #if labels[name] != code_addr:
      #   error('Oops, pass2 has different addresses')
   else:
      if name in labels:
         error('duplicate definition of label ' + name)
      labels[name] = code_addr  # this gets overriden if .EQU pseudo op

def scan_operand():
   global scan
   if scan[0].isalpha() or scan[0] == '_':
      name = scan_name()
      val = 0
      if name in labels:
         val = labels[name]
      elif pass2:
         error ('Unknown name %s, no label' % name)
   else:
      val = scan_num()
   operator = scan[0]
   if operator == '+' or operator == '-':      
      scan = scan[1:]
      val2 = scan_num()
      if operator == '-':  val2 = -val2
      val += val2
   return val

def scan_reg():
   reg = scan_operand()
   if reg < 0 or reg >16:  error('Expecting register')
   return reg

def org_directive():
   global scan, code_addr
   scan = scan[4:]
   skip_whitespace()
   code_addr = scan_operand()

def equ_directive():
   global scan
   scan = scan[4:]
   skip_whitespace()
   val = scan_operand()
   if not current_label:  error('Missing label')
   labels[current_label] = val # overrides usual code_addr value

def format1_variants():
   global scan
   if scan[0] == ',':  # long-address two-iword version
      # Pass1 needs syntactic hint for uses of fwd-ref far labels
      scan = scan[1:]  # don't allow spaces here
      val = scan_operand()
      emit448(basebits, 15, 0)
      emit(val)
   else:  # one-iword versions
      val = scan_operand()
      if scan[0] == '@':  # offset relative to dynamic reg value
         scan = scan[1:]
         rn = val
         displ = 0
         operator = scan[0]
         if operator == '+' or operator == '-':
            scan = scan[1:]
            displ = scan_operand()
            if operator == '-':  displ = -displ
         if pass2 and not (1 <= rn <= 14):
            error('Register-relative addressing works only for R1..R14') 
         emit448(basebits, rn, displ&0xff)
      else: # direct address
         val = scan_operand()
         emit448(basebits, 0, val)

def instr_line():
   name = scan_name(allow_at=True)
   if name not in opTable:
      error('Unrecognised opcode')  # error msg points well after the opcode
   format,basebits = opTable[name]
   skip_whitespace()

   if format == f1:  # mem/lit/Rn@+disp arg, possibly two iwords
      # SET ST ST@ PUSH INV DEC INC LD LD@ POP ADD SUB AND OR XOR
      format1_variants()
   elif format == f2:  # simple label or lit arg
      # BRA BGT BLT BGE BLE BNE BEQ ADI SBI
      val = scan_operand()
      emit448(basebits, 0, val)
   elif format == f3:  # no arg
      # RET OUT IN JMP@ NOP
      emit(basebits)
   elif format == f4:  # mem arg, two iwords
      # JMP CALL
      val =  scan_operand()
      emit(basebits)
      emit(val)
   else:  # format f5, special macros
      # LD ST with two reg args, mapping onto ld st LD@ or ST@
      if name == 'LD':
         r0 = scan_reg()
         if r0 != 0:  error('LD dest reg must be R0')
         comma()
         ind = atsign()
         rn = scan_reg()
         opnum = 9 if ind else 8  # LD@ or ld
      else: # 'ST'
          ind = atsign()
          rn = scan_reg()
          comma()
          r0 = scan_reg()
          if r0 != 0:  error('ST source reg must be R0')
          opnum = 3 if ind else 2  # ST@ or st
      emit448(opnum<<12, rn, 0)
   skip_whitespace()

def word_directive():
   global scan
   scan = scan[5:]
   skip_whitespace()
   while scan[0] != '\n':
      if scan[0] == "'" or scan[0] == '"':
         scan_quoted_string()
      else:
         val = scan_operand()
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

   # Historically, many memory-constrained assemblers did most work in a single pass,
   #   and then fixed up already-emitted incomplete fwd branch ops in a second half-pass.  
   #   That method is harder to apply to arbitrary target machines or label+nn forms,
   #   and is unneeded now with large fast host machines.

   global lineno, line, scan, code_addr, current_label, pass2
   pass2 = is_pass2
   code_addr = 0   # default, usually overridden by an initial #org directive
   lineno = 0
   for line in source_lines:
      lineno += 1
      #print (lineno, line[:-1])  ###
      scan = line
      current_label = ''
      if scan[0].isalpha() or scan[0] == '_':
         scan_label()
      skip_whitespace()
      if scan[0] == '\n':
         pass
      elif scan.startswith('.org'):
         org_directive()
      elif scan.startswith('.EQU') or scan.startswith('.equ'):
         equ_directive()
      elif scan.startswith('.WORD'):
         word_directive()
      elif scan[0].isalpha():
         instr_line()
      else:
         error('Expecting an assembler statement here')
      expect_eol()

def codedump(locvalpairs):
   next = -2
   s = ''
   for addr,cellval in locvalpairs:
      if len(s) >= 16*3+6 or addr != next:
         print(s)
         s = '%04X  ' % (addr*2)
         next = addr
      #s += '%04x ' % cellval
      s += '%02X %02X ' % (cellval>>8, cellval&0xff)
      next += 1
   print (s)
   print ()
   
def labeldump():
   namelocpairs = list(labels.items())
   namelocpairs.sort()  # alphabetical order
   for name,loc in namelocpairs:
      print ('%04x: %s' % (loc, name))
   print ()

def finals():
   locvalpairs = list(codemem.items())
   locvalpairs.sort()  # runtime location order
   codedump(locvalpairs)
   #labeldump()
      
# Main:
setups()
passover(False)  # Pass 1: discover label values
passover(True)   # Pass 2: translate and emit final instructions
finals()

# End!
