MINASS: A Minimal Assembler in Python3 for simple hobbyist CPU designs

Retargetable, by changing ~25 lines of opcode tables, and by adding Python code for parsing new source forms.
Output is absolute code as hexdump in Ascii.
Usage:  

python3 minass.py <yourprog.asm

This is an alternative to using retargetable cross-compilers like TASM (Telemark Assembler) or Meta16 whose sources are no longer available.

by Duane Sand, offered via MIT license

There are 3 branches in this repo:

slu4:    My rewrite of Carsten Herting's (Slu4) Python minimal assembler for his youtube 8-bit Minimal CPU project.

ken2020: An alternative to using TASM for Ken Boak's Suite-16 2020 variant on Wozniak's Sweet-16 VM on Apple-2 computers.

ken2025: Revision of ken2020 to handle Ken's 2025 evolution of his Suite-16 ISA.
