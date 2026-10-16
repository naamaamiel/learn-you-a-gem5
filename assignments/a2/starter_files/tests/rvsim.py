
import argparse
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAMS = ["chain_add", "chain_mul", "chain_div", "indep_add", "kernel"]

M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
SIGN = 1 << 63
STACK_TOP = 0x7FFF_FFFF_F000  # one past the highest stack byte
STACK_SIZE = 1 << 20
SP_INIT = STACK_TOP - 0x400   # 16-byte aligned, below room for argv/auxv
MAX_STEPS = 200_000_000


class SimError(Exception):
    """The program is broken, or does something rvsim doesn't support."""


class ProgramExit(Exception):
    """The program called exit."""


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def s64(value):
    return value - (1 << 64) if value >> 63 else value


# ---------------------------------------------------------------------------
# ELF
# ---------------------------------------------------------------------------

class Segment:
    def __init__(self, vaddr, data, flags, offset, filesz):
        self.start, self.end = vaddr, vaddr + len(data)
        self.data, self.flags = data, flags
        self.offset, self.filesz = offset, filesz


def read_elf(path):
    """Parse a static RV64 executable from its bytes.

    Returns (entry, segments, sections, info, problems), where problems lists
    every way the file departs from what gem5's SE loader expects.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) < 64 or raw[:4] != b"\x7fELF":
        raise SimError(f"{path}: not an ELF file")
    if raw[4] != 2 or raw[5] != 1:
        raise SimError(f"{path}: not a 64-bit little-endian ELF file")
    problems = []

    def expect(ok, msg):
        if not ok:
            problems.append(msg)

    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
     e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
     e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
    expect(raw[6] == 1, "EI_VERSION is not EV_CURRENT")
    expect(e_type == 2, f"e_type is {e_type}, not ET_EXEC")
    expect(e_machine == 243, f"e_machine is {e_machine}, not EM_RISCV")
    expect(e_version == 1, f"e_version is {e_version}")
    expect(e_ehsize == 64, f"e_ehsize is {e_ehsize}")
    expect(e_phentsize == 56, f"e_phentsize is {e_phentsize}")
    info = {"entry": e_entry, "e_flags": e_flags, "osabi": raw[7]}

    segments = []
    for n in range(e_phnum):
        (p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz,
         p_align) = struct.unpack_from("<IIQQQQQQ", raw,
                                       e_phoff + n * e_phentsize)
        expect(p_type != 3, "has PT_INTERP: not a static executable")
        if p_type != 1:
            continue
        expect(p_offset + p_filesz <= len(raw),
               f"PT_LOAD {n} runs past the end of the file")
        expect(p_filesz <= p_memsz, f"PT_LOAD {n}: p_filesz > p_memsz")
        expect(p_paddr == p_vaddr,
               f"PT_LOAD {n}: p_paddr {p_paddr:#x} != p_vaddr {p_vaddr:#x} "
               "(gem5 places segments at p_paddr)")
        expect(p_align <= 1 or (p_align & (p_align - 1) == 0
                                and p_offset % p_align == p_vaddr % p_align),
               f"PT_LOAD {n}: p_offset and p_vaddr differ modulo p_align")
        data = bytearray(raw[p_offset:p_offset + p_filesz])
        data += bytes(p_memsz - p_filesz)
        segments.append(Segment(p_vaddr, data, p_flags, p_offset, p_filesz))
    expect(segments, "no PT_LOAD segment")
    expect(any(s.start <= e_entry < s.end and s.flags & 1 for s in segments),
           f"entry point {e_entry:#x} is not in an executable segment")

    sections = {}
    if not e_shnum:
        problems.append("no section headers (gem5 walks them through "
                        "e_shstrndx)")
    elif (e_shentsize != 64 or e_shoff + 64 * e_shnum > len(raw)
          or e_shstrndx >= e_shnum):
        problems.append("bad section header table or e_shstrndx")
    else:
        headers = [struct.unpack_from("<IIQQQQIIQQ", raw, e_shoff + 64 * n)
                   for n in range(e_shnum)]
        expect(headers[0] == (0,) * 10, "section 0 is not the null section")
        strtab_hdr = headers[e_shstrndx]
        expect(strtab_hdr[1] == 3, "e_shstrndx is not a SHT_STRTAB section")
        strtab = raw[strtab_hdr[4]:strtab_hdr[4] + strtab_hdr[5]]
        for (name, stype, sflags, addr, offset, size, _link, _info, _align,
             _entsize) in headers[1:]:
            end = strtab.find(b"\0", name)
            sname = (strtab[name:end].decode("ascii", "replace")
                     if name < len(strtab) and end >= 0 else f"?{name}")
            sections[sname] = {"type": stype, "flags": sflags, "addr": addr,
                               "offset": offset, "size": size}
    return e_entry, segments, sections, info, problems


# ---------------------------------------------------------------------------
# Decoding, from the opcode map and the instruction formats in the spec
# ---------------------------------------------------------------------------

FMT = {0: "s", 1: "d", 2: "h", 3: "q"}
RM_NAME = {0: "rne", 1: "rtz", 2: "rdn", 3: "rup", 4: "rmm", 7: "dyn"}
BRANCH_F3 = {0: "beq", 1: "bne", 4: "blt", 5: "bge", 6: "bltu", 7: "bgeu"}
LOAD_F3 = {0: "lb", 1: "lh", 2: "lw", 3: "ld", 4: "lbu", 5: "lhu", 6: "lwu"}
STORE_F3 = {0: "sb", 1: "sh", 2: "sw", 3: "sd"}
OPIMM_F3 = {0: "addi", 2: "slti", 3: "sltiu", 4: "xori", 6: "ori", 7: "andi"}
OP_F7F3 = {
    (0x00, 0): "add", (0x20, 0): "sub", (0x00, 1): "sll", (0x00, 2): "slt",
    (0x00, 3): "sltu", (0x00, 4): "xor", (0x00, 5): "srl", (0x20, 5): "sra",
    (0x00, 6): "or", (0x00, 7): "and",
    (0x01, 0): "mul", (0x01, 1): "mulh", (0x01, 2): "mulhsu",
    (0x01, 3): "mulhu", (0x01, 4): "div", (0x01, 5): "divu",
    (0x01, 6): "rem", (0x01, 7): "remu",
}
OP32_F7F3 = {
    (0x00, 0): "addw", (0x20, 0): "subw", (0x00, 1): "sllw",
    (0x00, 5): "srlw", (0x20, 5): "sraw", (0x01, 0): "mulw",
    (0x01, 4): "divw", (0x01, 5): "divuw", (0x01, 6): "remw",
    (0x01, 7): "remuw",
}
CSR_F3 = {1: "csrrw", 2: "csrrs", 3: "csrrc", 5: "csrrwi", 6: "csrrsi",
          7: "csrrci"}
FMA_OPCODES = {0x43: "fmadd", 0x47: "fmsub", 0x4B: "fnmsub", 0x4F: "fnmadd"}
INT_TYPES = {0: "w", 1: "wu", 2: "l", 3: "lu"}
MUL_OPS = {"mul", "mulh", "mulhsu", "mulhu", "mulw"}
DIV_OPS = {"div", "divu", "rem", "remu", "divw", "divuw", "remw", "remuw"}


class Inst:
    """A decoded instruction. dest is the register file it writes, if any."""
    __slots__ = ("pc", "word", "mnem", "kind", "text", "opclass", "dest",
                 "rd", "rs1", "rs2", "rs3", "imm", "rm", "fmt")


def decode(word, pc=0):
    d = Inst()
    d.pc, d.word = pc, word
    rd = d.rd = (word >> 7) & 31
    rs1 = d.rs1 = (word >> 15) & 31
    rs2 = d.rs2 = (word >> 20) & 31
    d.rs3 = word >> 27
    d.rm = f3 = (word >> 12) & 7
    d.fmt = (word >> 25) & 3
    opcode, f7 = word & 0x7F, word >> 25

    def out(mnem, kind, args=(), dest=None, opclass="IntAlu", imm=0):
        d.mnem, d.kind, d.dest, d.opclass, d.imm = mnem, kind, dest, opclass, imm
        d.text = mnem + (" " + ", ".join(args) if args else "")
        return d

    def illegal():
        return out(".word", "illegal", [f"{word:#010x}"], opclass="-")

    def x(r):
        return f"x{r}"

    def f(r):
        return f"f{r}"

    if word & 0b11 != 0b11 or word & 0b11100 == 0b11100:
        return illegal()  # a 16-bit (compressed) or a longer-than-32-bit encoding
    imm_i = sext(word >> 20, 12)
    imm_s = sext(f7 << 5 | rd, 12)
    imm_b = sext((word >> 31) << 12 | ((word >> 7) & 1) << 11
                 | ((word >> 25) & 0x3F) << 5 | ((word >> 8) & 0xF) << 1, 13)
    imm_u = sext(word & 0xFFFFF000, 32)
    imm_j = sext((word >> 31) << 20 | ((word >> 12) & 0xFF) << 12
                 | ((word >> 20) & 1) << 11 | ((word >> 21) & 0x3FF) << 1, 21)
    rmn = RM_NAME.get(f3, f"rm{f3}")

    if opcode == 0x37:
        return out("lui", "lui", [x(rd), f"{word >> 12:#x}"], "x", imm=imm_u)
    if opcode == 0x17:
        return out("auipc", "auipc", [x(rd), f"{word >> 12:#x}"], "x",
                   imm=imm_u)
    if opcode == 0x6F:
        return out("jal", "jal", [x(rd), str(imm_j)], "x", imm=imm_j)
    if opcode == 0x67 and f3 == 0:
        return out("jalr", "jalr", [x(rd), f"{imm_i}({x(rs1)})"], "x",
                   imm=imm_i)
    if opcode == 0x63 and f3 in BRANCH_F3:
        return out(BRANCH_F3[f3], "branch", [x(rs1), x(rs2), str(imm_b)],
                   imm=imm_b)
    if opcode == 0x03 and f3 in LOAD_F3:
        return out(LOAD_F3[f3], "load", [x(rd), f"{imm_i}({x(rs1)})"], "x",
                   "MemRead", imm_i)
    if opcode == 0x23 and f3 in STORE_F3:
        return out(STORE_F3[f3], "store", [x(rs2), f"{imm_s}({x(rs1)})"],
                   None, "MemWrite", imm_s)
    if opcode == 0x13:
        if f3 in (1, 5):  # RV64: 6-bit shamt, imm[11:6] selects the shift
            name = {(1, 0): "slli", (5, 0): "srli",
                    (5, 0x10): "srai"}.get((f3, word >> 26))
            if name is None:
                return illegal()
            shamt = (word >> 20) & 0x3F
            return out(name, "alui", [x(rd), x(rs1), str(shamt)], "x",
                       imm=shamt)
        return out(OPIMM_F3[f3], "alui", [x(rd), x(rs1), str(imm_i)], "x",
                   imm=imm_i)
    if opcode == 0x1B:
        if f3 == 0:
            return out("addiw", "alui", [x(rd), x(rs1), str(imm_i)], "x",
                       imm=imm_i)
        name = {(1, 0): "slliw", (5, 0): "srliw",
                (5, 0x20): "sraiw"}.get((f3, f7))
        if name is None:
            return illegal()
        return out(name, "alui", [x(rd), x(rs1), str(rs2)], "x", imm=rs2)
    if opcode in (0x33, 0x3B):
        name = (OP_F7F3 if opcode == 0x33 else OP32_F7F3).get((f7, f3))
        if name is None:
            return illegal()
        opclass = ("IntMult" if name in MUL_OPS else
                   "IntDiv" if name in DIV_OPS else "IntAlu")
        return out(name, "alu", [x(rd), x(rs1), x(rs2)], "x", opclass)
    if opcode == 0x0F:
        if f3 == 0:
            return out("fence", "nop", opclass="No_OpClass")
        if f3 == 1:
            return out("fence.i", "nop", opclass="No_OpClass")
        return illegal()
    if opcode == 0x73:
        if word == 0x00000073:
            return out("ecall", "ecall", opclass="No_OpClass")
        if word == 0x00100073:
            return out("ebreak", "illegal", opclass="No_OpClass")
        if f3 in CSR_F3:
            src = x(rs1) if f3 < 4 else str(rs1)
            return out(CSR_F3[f3], "csr", [x(rd), f"{word >> 20:#x}", src],
                       "x", "No_OpClass", imm=word >> 20)
        return illegal()
    if opcode == 0x07 and f3 in (2, 3):
        return out("flw" if f3 == 2 else "fld", "fload",
                   [f(rd), f"{imm_i}({x(rs1)})"], "f", "FloatMemRead", imm_i)
    if opcode == 0x27 and f3 in (2, 3):
        return out("fsw" if f3 == 2 else "fsd", "fstore",
                   [f(rs2), f"{imm_s}({x(rs1)})"], None, "FloatMemWrite",
                   imm_s)
    if opcode in FMA_OPCODES and d.fmt in (0, 1):
        return out(f"{FMA_OPCODES[opcode]}.{FMT[d.fmt]}", "fma",
                   [f(rd), f(rs1), f(rs2), f(d.rs3), rmn], "f", "FloatMultAcc")
    if opcode != 0x53:
        return illegal()

    # OP-FP: funct7 = funct5 | fmt
    f5, fs = word >> 27, FMT[d.fmt]
    if f5 <= 0b00011:
        return out(f"{('fadd', 'fsub', 'fmul', 'fdiv')[f5]}.{fs}", "fp3",
                   [f(rd), f(rs1), f(rs2), rmn], "f",
                   ("FloatAdd", "FloatAdd", "FloatMult", "FloatDiv")[f5])
    if f5 == 0b01011 and rs2 == 0:
        return out(f"fsqrt.{fs}", "fsqrt", [f(rd), f(rs1), rmn], "f",
                   "FloatSqrt")
    if f5 == 0b00100 and f3 <= 2:
        return out(f"{('fsgnj', 'fsgnjn', 'fsgnjx')[f3]}.{fs}", "fsgnj",
                   [f(rd), f(rs1), f(rs2)], "f", "FloatMisc")
    if f5 == 0b00101 and f3 <= 1:
        return out(f"{('fmin', 'fmax')[f3]}.{fs}", "fminmax",
                   [f(rd), f(rs1), f(rs2)], "f", "FloatCmp")
    if f5 == 0b01000 and rs2 in FMT and rs2 != d.fmt:
        return out(f"fcvt.{fs}.{FMT[rs2]}", "fcvt_ff", [f(rd), f(rs1), rmn],
                   "f", "FloatCvt")
    if f5 == 0b10100 and f3 <= 2:
        return out(f"{('fle', 'flt', 'feq')[f3]}.{fs}", "fcmp",
                   [x(rd), f(rs1), f(rs2)], "x", "FloatCmp")
    if f5 == 0b11000 and rs2 in INT_TYPES:
        return out(f"fcvt.{INT_TYPES[rs2]}.{fs}", "fcvt_fi",
                   [x(rd), f(rs1), rmn], "x", "FloatCvt")
    if f5 == 0b11010 and rs2 in INT_TYPES:
        return out(f"fcvt.{fs}.{INT_TYPES[rs2]}", "fcvt_if",
                   [f(rd), x(rs1), rmn], "f", "FloatCvt")
    fmv = "w" if fs == "s" else fs  # fmv.x.w / fmv.w.x for single precision
    if f5 == 0b11100 and rs2 == 0 and f3 == 0:
        return out(f"fmv.x.{fmv}", "fmv_xf", [x(rd), f(rs1)], "x", "FloatCvt")
    if f5 == 0b11100 and rs2 == 0 and f3 == 1:
        return out(f"fclass.{fs}", "fclass", [x(rd), f(rs1)], "x",
                   "FloatMisc")
    if f5 == 0b11110 and rs2 == 0 and f3 == 0:
        return out(f"fmv.{fmv}.x", "fmv_fx", [f(rd), x(rs1)], "f", "FloatCvt")
    return illegal()


# Encodings worked out by hand from the manual's tables; decode() must agree.
DECODER_SELF_TEST = {
    0x00000013: "addi x0, x0, 0",
    0x00000073: "ecall",
    0x00008067: "jalr x0, 0(x1)",
    0x05D00893: "addi x17, x0, 93",
    0x02B50533: "mul x10, x10, x11",
    0x02B54533: "div x10, x10, x11",
    0xFE051EE3: "bne x10, x0, -4",
    0x12345537: "lui x10, 0x12345",
    0x00A10023: "sb x10, 0(x2)",
    0x00351513: "slli x10, x10, 3",
    0x0035D513: "srli x10, x11, 3",
    0x4035D513: "srai x10, x11, 3",
    0x02B57553: "fadd.d f10, f10, f11, dyn",
    0xE2050553: "fmv.x.d x10, f10",
    0xF2050553: "fmv.d.x f10, x10",
    0xC2251553: "fcvt.l.d x10, f10, rtz",
    0xD2257553: "fcvt.d.l f10, x10, dyn",
}


# ---------------------------------------------------------------------------
# Integer semantics
# ---------------------------------------------------------------------------

def _div(a, b, bits):
    a, b = sext(a, bits), sext(b, bits)
    if b == 0:
        return -1
    if a == -(1 << (bits - 1)) and b == -1:
        return a
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _rem(a, b, bits):
    a, b = sext(a, bits), sext(b, bits)
    if b == 0:
        return a
    if a == -(1 << (bits - 1)) and b == -1:
        return 0
    r = abs(a) % abs(b)
    return -r if a < 0 else r


def _divu(a, b, bits):
    a, b = a & ((1 << bits) - 1), b & ((1 << bits) - 1)
    return (1 << bits) - 1 if b == 0 else a // b


def _remu(a, b, bits):
    a, b = a & ((1 << bits) - 1), b & ((1 << bits) - 1)
    return a if b == 0 else a % b


def _w(value):
    return sext(value, 32) & M64


ALU = {
    "add": lambda a, b: (a + b) & M64,
    "sub": lambda a, b: (a - b) & M64,
    "sll": lambda a, b: (a << (b & 63)) & M64,
    "slt": lambda a, b: int(s64(a) < s64(b)),
    "sltu": lambda a, b: int(a < b),
    "xor": lambda a, b: a ^ b,
    "srl": lambda a, b: a >> (b & 63),
    "sra": lambda a, b: (s64(a) >> (b & 63)) & M64,
    "or": lambda a, b: a | b,
    "and": lambda a, b: a & b,
    "mul": lambda a, b: (a * b) & M64,
    "mulh": lambda a, b: ((s64(a) * s64(b)) >> 64) & M64,
    "mulhsu": lambda a, b: ((s64(a) * b) >> 64) & M64,
    "mulhu": lambda a, b: (a * b) >> 64,
    "div": lambda a, b: _div(a, b, 64) & M64,
    "divu": lambda a, b: _divu(a, b, 64),
    "rem": lambda a, b: _rem(a, b, 64) & M64,
    "remu": lambda a, b: _remu(a, b, 64),
    "addw": lambda a, b: _w(a + b),
    "subw": lambda a, b: _w(a - b),
    "sllw": lambda a, b: _w(a << (b & 31)),
    "srlw": lambda a, b: _w((a & M32) >> (b & 31)),
    "sraw": lambda a, b: _w(sext(a, 32) >> (b & 31)),
    "mulw": lambda a, b: _w(a * b),
    "divw": lambda a, b: _w(_div(a, b, 32)),
    "divuw": lambda a, b: _w(_divu(a, b, 32)),
    "remw": lambda a, b: _w(_rem(a, b, 32)),
    "remuw": lambda a, b: _w(_remu(a, b, 32)),
}
ALU_IMM = {  # the immediate is already sign-extended
    "addi": lambda a, i: (a + i) & M64,
    "slti": lambda a, i: int(s64(a) < i),
    "sltiu": lambda a, i: int(a < i & M64),
    "xori": lambda a, i: a ^ (i & M64),
    "ori": lambda a, i: a | (i & M64),
    "andi": lambda a, i: a & i & M64,
    "slli": lambda a, i: (a << i) & M64,
    "srli": lambda a, i: a >> i,
    "srai": lambda a, i: (s64(a) >> i) & M64,
    "addiw": lambda a, i: _w(a + i),
    "slliw": lambda a, i: _w(a << i),
    "srliw": lambda a, i: _w((a & M32) >> i),
    "sraiw": lambda a, i: _w(sext(a, 32) >> i),
}
BRANCH_TAKEN = {
    "beq": lambda a, b: a == b,
    "bne": lambda a, b: a != b,
    "blt": lambda a, b: s64(a) < s64(b),
    "bge": lambda a, b: s64(a) >= s64(b),
    "bltu": lambda a, b: a < b,
    "bgeu": lambda a, b: a >= b,
}
LOAD_SIZE = {"lb": (1, True), "lh": (2, True), "lw": (4, True),
             "ld": (8, False), "lbu": (1, False), "lhu": (2, False),
             "lwu": (4, False)}
STORE_SIZE = {"sb": 1, "sh": 2, "sw": 4, "sd": 8}


# ---------------------------------------------------------------------------
# Double-precision semantics: exact integer arithmetic, then one rounding
# ---------------------------------------------------------------------------

NV, DZ, OF, UF, NX = 0x10, 0x08, 0x04, 0x02, 0x01
RNE, RTZ, RDN, RUP, RMM = range(5)
FRAC = (1 << 52) - 1
MAG = SIGN - 1
INF = 0x7FF0000000000000
QNAN = 0x7FF8000000000000  # the canonical NaN
MAX_FINITE = 0x7FEFFFFFFFFFFFFF


def flag_names(flags):
    return " ".join(n for n, b in (("NV", NV), ("DZ", DZ), ("OF", OF),
                                   ("UF", UF), ("NX", NX)) if flags & b)


def is_nan(b):
    return b & MAG > INF


def is_snan(b):
    return is_nan(b) and not b >> 51 & 1


def is_inf(b):
    return b & MAG == INF


def is_zero(b):
    return b & MAG == 0


def unpack(b):
    """A finite double as (sign, mant, exp): (-1)**sign * mant * 2**exp."""
    e = (b >> 52) & 0x7FF
    if e == 0:
        return b >> 63, b & FRAC, -1074
    return b >> 63, (b & FRAC) | 1 << 52, e - 1075


def round_up(rm, sign, kept, rest, half):
    """Whether rounding kept (with the dropped part rest, half = one half
    unit of kept's last bit) moves the magnitude up."""
    if rm == RNE:
        return rest > half or (rest == half and kept & 1)
    if rm == RTZ:
        return False
    if rm == RDN:
        return sign == 1
    if rm == RUP:
        return sign == 0
    return rest >= half  # RMM


def round_pack(sign, mant, exp, rm):
    """(-1)**sign * mant * 2**exp (mant > 0) rounded to a double: (bits, flags)."""
    lead = exp + mant.bit_length() - 1  # 2**lead <= magnitude < 2**(lead + 1)
    q = max(lead - 52, -1074)           # weight of the result's last bit
    flags = 0
    if q > exp:
        drop = q - exp
        kept, rest = mant >> drop, mant & ((1 << drop) - 1)
        if rest:
            flags = NX
            kept += round_up(rm, sign, kept, rest, 1 << (drop - 1))
    else:
        kept = mant << (exp - q)
    if kept >> 53:  # rounding carried into a 54th bit
        kept >>= 1
        q += 1
    if kept >> 52:  # normal
        biased = q + 1075
        if biased >= 0x7FF:
            to_inf = (rm in (RNE, RMM) or (rm == RUP and not sign)
                      or (rm == RDN and sign))
            return sign << 63 | (INF if to_inf else MAX_FINITE), OF | NX
        return sign << 63 | biased << 52 | (kept & FRAC), flags
    if flags:  # subnormal or zero, and inexact
        flags |= UF
    return sign << 63 | kept, flags


def _nan_result(*operands):
    return QNAN, NV if any(is_snan(b) for b in operands) else 0


def f64_add(a, b, rm):
    if is_nan(a) or is_nan(b):
        return _nan_result(a, b)
    if is_inf(a) or is_inf(b):
        if is_inf(a) and is_inf(b) and (a ^ b) >> 63:
            return QNAN, NV
        return (a if is_inf(a) else b), 0
    sa, ma, ea = unpack(a)
    sb, mb, eb = unpack(b)
    e = min(ea, eb)
    total = ((-1) ** sa * (ma << (ea - e))) + ((-1) ** sb * (mb << (eb - e)))
    if total == 0:
        if ma == 0 and mb == 0:
            sign = (sa | sb) if rm == RDN else (sa & sb)
        else:
            sign = 1 if rm == RDN else 0
        return sign << 63, 0
    return round_pack(int(total < 0), abs(total), e, rm)


def f64_sub(a, b, rm):
    return f64_add(a, b ^ SIGN, rm) if not is_nan(b) else _nan_result(a, b)


def f64_mul(a, b, rm):
    if is_nan(a) or is_nan(b):
        return _nan_result(a, b)
    sign = (a ^ b) >> 63
    if is_inf(a) or is_inf(b):
        if is_zero(a) or is_zero(b):
            return QNAN, NV
        return sign << 63 | INF, 0
    _, ma, ea = unpack(a)
    _, mb, eb = unpack(b)
    if ma == 0 or mb == 0:
        return sign << 63, 0
    return round_pack(sign, ma * mb, ea + eb, rm)


def f64_div(a, b, rm):
    if is_nan(a) or is_nan(b):
        return _nan_result(a, b)
    sign = (a ^ b) >> 63
    if is_inf(a):
        return (QNAN, NV) if is_inf(b) else (sign << 63 | INF, 0)
    if is_inf(b):
        return sign << 63, 0
    _, ma, ea = unpack(a)
    _, mb, eb = unpack(b)
    if mb == 0:
        return (QNAN, NV) if ma == 0 else (sign << 63 | INF, DZ)
    if ma == 0:
        return sign << 63, 0
    shift = max(0, 128 + mb.bit_length() - ma.bit_length())
    quot, rest = divmod(ma << shift, mb)
    # The sticky bit stands for the nonzero remainder, far below the rounding point.
    return round_pack(sign, quot << 1 | (rest != 0), ea - eb - shift - 1, rm)


def f64_sqrt(a, rm):
    if is_nan(a):
        return _nan_result(a)
    if is_zero(a):
        return a, 0
    if a >> 63:
        return QNAN, NV
    if is_inf(a):
        return a, 0
    _, m, e = unpack(a)
    if e & 1:
        m, e = m << 1, e - 1
    m, e = m << 256, e - 256
    root = math.isqrt(m)
    return round_pack(0, root << 1 | (root * root != m), e // 2 - 1, rm)


def f64_fma(a, b, c, rm, negate_product, negate_addend):
    if negate_product:
        a ^= SIGN
    if negate_addend:
        c ^= SIGN
    if is_nan(a) or is_nan(b) or is_nan(c):
        inf_times_zero = ((is_inf(a) and is_zero(b))
                          or (is_zero(a) and is_inf(b)))
        q, flags = _nan_result(a, b, c)
        return q, flags | (NV if inf_times_zero else 0)
    psign = (a ^ b) >> 63
    if is_inf(a) or is_inf(b):
        if is_zero(a) or is_zero(b):
            return QNAN, NV
        if is_inf(c) and c >> 63 != psign:
            return QNAN, NV
        return psign << 63 | INF, 0
    if is_inf(c):
        return c, 0
    _, ma, ea = unpack(a)
    _, mb, eb = unpack(b)
    sc, mc, ec = unpack(c)
    mp, ep = ma * mb, ea + eb
    e = min(ep, ec)
    total = ((-1) ** psign * (mp << (ep - e))) + ((-1) ** sc * (mc << (ec - e)))
    if total == 0:
        if mp == 0 and mc == 0:
            sign = (psign | sc) if rm == RDN else (psign & sc)
        else:
            sign = 1 if rm == RDN else 0
        return sign << 63, 0
    return round_pack(int(total < 0), abs(total), e, rm)


def f64_from_int(value, rm):
    if value == 0:
        return 0, 0
    return round_pack(int(value < 0), abs(value), 0, rm)


def f64_to_int(b, rm, lo, hi):
    """Round to an integer in [lo, hi]; out of range saturates, with NV."""
    if is_nan(b):
        return hi, NV
    if is_inf(b):
        return (lo if b >> 63 else hi), NV
    sign, mant, exp = unpack(b)
    rest = 0
    if exp >= 0:
        kept = mant << exp
    else:
        drop = -exp
        kept, rest = mant >> drop, mant & ((1 << drop) - 1)
        if rest:
            kept += round_up(rm, sign, kept, rest, 1 << (drop - 1))
    n = -kept if sign else kept
    if n < lo:
        return lo, NV
    if n > hi:
        return hi, NV
    return n, NX if rest else 0


def f64_key(b):
    """An integer that orders non-NaN doubles like their values."""
    return -(b & MAG) if b >> 63 else b & MAG


def f64_compare(a, b, op):
    if is_nan(a) or is_nan(b):
        signaling = op != "feq" or is_snan(a) or is_snan(b)
        return 0, NV if signaling else 0
    ka, kb = f64_key(a), f64_key(b)
    return int({"feq": ka == kb, "flt": ka < kb, "fle": ka <= kb}[op]), 0


def f64_minmax(a, b, want_max):
    flags = NV if is_snan(a) or is_snan(b) else 0
    if is_nan(a) and is_nan(b):
        return QNAN, flags
    if is_nan(a):
        return b, flags
    if is_nan(b):
        return a, flags
    ka, kb = f64_key(a), f64_key(b)
    if ka == kb:  # equal, or zeros of both signs: -0 < +0 here
        return (a & b if want_max else a | b), flags
    return (a if (ka > kb) == want_max else b), flags


def f64_class(b):
    sign = b >> 63
    if is_nan(b):
        return 1 << 8 if is_snan(b) else 1 << 9
    if is_inf(b):
        return 1 << 0 if sign else 1 << 7
    if is_zero(b):
        return 1 << 3 if sign else 1 << 4
    if (b >> 52) & 0x7FF == 0:
        return 1 << 2 if sign else 1 << 5
    return 1 << 1 if sign else 1 << 6


# ---------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------

class Machine:
    def __init__(self, entry, segments):
        self.x = [0] * 32
        self.f = [0] * 32  # raw 64-bit patterns
        self.fflags = 0
        self.frm = 0
        self.pc = entry
        # [start, end, data, writable, executable]
        self.regions = [[s.start, s.end, s.data, bool(s.flags & 2),
                         bool(s.flags & 1)] for s in segments]
        self.regions.append([STACK_TOP - STACK_SIZE, STACK_TOP,
                             bytearray(STACK_SIZE), True, False])
        self.x[2] = SP_INIT
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.syscalls = []
        self.exit_code = None
        self.cache = {}  # pc -> [closure, Inst, count]
        self.steps = 0

    def region(self, addr, size, write=False, execute=False):
        for r in self.regions:
            if r[0] <= addr and addr + size <= r[1]:
                if write and not r[3]:
                    raise SimError(f"store to read-only address {addr:#x}")
                if execute and not r[4]:
                    raise SimError(f"fetch from non-executable {addr:#x}")
                return r
        raise SimError(f"access to unmapped address {addr:#x} ({size} bytes)")

    def load(self, addr, size, signed):
        r = self.region(addr, size)
        value = int.from_bytes(r[2][addr - r[0]:addr - r[0] + size], "little")
        return sext(value, 8 * size) & M64 if signed else value

    def store(self, addr, size, value):
        r = self.region(addr, size, write=True)
        r[2][addr - r[0]:addr - r[0] + size] = \
            (value & ((1 << 8 * size) - 1)).to_bytes(size, "little")

    def read_bytes(self, addr, size):
        if size == 0:
            return b""
        r = self.region(addr, size)
        return bytes(r[2][addr - r[0]:addr - r[0] + size])

    def rounding(self, rm):
        if rm == 7:
            rm = self.frm
        if rm > 4:
            raise SimError(f"reserved rounding mode {rm}")
        return rm

    def csr(self, num, value=None):
        """Read the FP CSR num, and write value to it if it isn't None."""
        if num not in (1, 2, 3):
            raise SimError(f"CSR {num:#x} is not implemented")
        old = {1: self.fflags, 2: self.frm,
               3: self.frm << 5 | self.fflags}[num]
        if value is not None:
            if num in (1, 3):
                self.fflags = value & 0x1F
            if num == 2:
                self.frm = value & 7
            if num == 3:
                self.frm = (value >> 5) & 7
        return old

    def syscall(self):
        num, a0, a1, a2 = self.x[17], self.x[10], self.x[11], self.x[12]
        if num == 64:  # write(fd, buf, count)
            data = self.read_bytes(a1, a2)
            if a0 == 1:
                self.stdout += data
            elif a0 == 2:
                self.stderr += data
            else:
                raise SimError(f"write to fd {a0}")
            self.syscalls.append({"call": "write", "fd": a0, "bytes": a2})
            self.x[10] = a2
        elif num in (93, 94):  # exit, exit_group
            self.syscalls.append({"call": "exit", "status": s64(a0)})
            self.exit_code = s64(a0)
            raise ProgramExit
        else:
            raise SimError(f"syscall {num} is not implemented")

    def entry_at(self, pc):
        if pc & 3:
            raise SimError(f"misaligned pc {pc:#x}")
        r = self.region(pc, 4, execute=True)
        word = int.from_bytes(r[2][pc - r[0]:pc - r[0] + 4], "little")
        d = decode(word, pc)
        ent = self.cache[pc] = [build(d, self), d, 0]
        return ent

    def run(self, max_steps=MAX_STEPS):
        x, cache, pc = self.x, self.cache, self.pc
        steps = 0
        try:
            for steps in range(1, max_steps + 1):
                ent = cache.get(pc)
                if ent is None:
                    ent = self.entry_at(pc)
                ent[2] += 1
                pc = ent[0]()
                x[0] = 0
        except ProgramExit:
            self.steps = steps
            return
        except SimError as e:
            raise SimError(f"at pc {pc:#x} after {steps} instructions: {e}")
        raise SimError(f"no exit after {max_steps} instructions")


def build(d, m):
    """A closure that executes d on m and returns the next pc."""
    xr, fr = m.x, m.f
    rd, rs1, rs2, imm, kind, mnem = d.rd, d.rs1, d.rs2, d.imm, d.kind, d.mnem
    nxt = (d.pc + 4) & M64

    if kind == "alu":
        if mnem == "add":
            def run():
                xr[rd] = (xr[rs1] + xr[rs2]) & M64
                return nxt
        elif mnem == "xor":
            def run():
                xr[rd] = xr[rs1] ^ xr[rs2]
                return nxt
        elif mnem == "mul":
            def run():
                xr[rd] = (xr[rs1] * xr[rs2]) & M64
                return nxt
        else:
            fn = ALU[mnem]

            def run():
                xr[rd] = fn(xr[rs1], xr[rs2])
                return nxt
        return run
    if kind == "alui":
        if mnem == "addi":
            def run():
                xr[rd] = (xr[rs1] + imm) & M64
                return nxt
        else:
            fn = ALU_IMM[mnem]

            def run():
                xr[rd] = fn(xr[rs1], imm)
                return nxt
        return run
    if kind in ("lui", "auipc"):
        value = (imm if kind == "lui" else d.pc + imm) & M64

        def run():
            xr[rd] = value
            return nxt
        return run
    if kind == "branch":
        target = (d.pc + imm) & M64
        if mnem == "bne":
            def run():
                return target if xr[rs1] != xr[rs2] else nxt
        else:
            taken = BRANCH_TAKEN[mnem]

            def run():
                return target if taken(xr[rs1], xr[rs2]) else nxt
        return run
    if kind == "jal":
        target = (d.pc + imm) & M64

        def run():
            xr[rd] = nxt
            return target
        return run
    if kind == "jalr":
        def run():
            target = (xr[rs1] + imm) & M64 & ~1
            xr[rd] = nxt
            return target
        return run
    if kind == "load":
        size, signed = LOAD_SIZE[mnem]

        def run():
            xr[rd] = m.load((xr[rs1] + imm) & M64, size, signed)
            return nxt
        return run
    if kind == "store":
        size = STORE_SIZE[mnem]

        def run():
            m.store((xr[rs1] + imm) & M64, size, xr[rs2])
            return nxt
        return run
    if kind == "ecall":
        def run():
            m.syscall()
            return nxt
        return run
    if kind == "nop":
        return lambda: nxt
    if kind == "csr":
        f3, num = d.rm, imm

        def run():
            src = xr[rs1] if f3 < 4 else rs1
            if f3 & 3 == 1:  # csrrw(i)
                old = m.csr(num, src)
            else:
                old = m.csr(num)
                if rs1:  # x0 / uimm 0: read only
                    m.csr(num, old | src if f3 & 3 == 2 else old & ~src)
            xr[rd] = old
            return nxt
        return run

    def fail(why):
        def run():
            raise SimError(f"{why}: {d.text} ({d.word:#010x})")
        return run

    if kind == "illegal":
        return fail("illegal instruction")
    if kind == "fload":
        if mnem != "fld":
            return fail("single precision is not implemented")

        def run():
            fr[rd] = m.load((xr[rs1] + imm) & M64, 8, False)
            return nxt
        return run
    if kind == "fstore":
        if mnem != "fsd":
            return fail("single precision is not implemented")

        def run():
            m.store((xr[rs1] + imm) & M64, 8, fr[rs2])
            return nxt
        return run
    if d.fmt != 1 or kind == "fcvt_ff":
        return fail("only double precision is implemented")
    static_rm = d.rm

    if kind == "fp3":
        op = {"fadd": f64_add, "fsub": f64_sub, "fmul": f64_mul,
              "fdiv": f64_div}[mnem.split(".")[0]]

        def run():
            fr[rd], flags = op(fr[rs1], fr[rs2], m.rounding(static_rm))
            m.fflags |= flags
            return nxt
        return run
    if kind == "fsqrt":
        def run():
            fr[rd], flags = f64_sqrt(fr[rs1], m.rounding(static_rm))
            m.fflags |= flags
            return nxt
        return run
    if kind == "fma":
        rs3 = d.rs3
        neg_p, neg_c = {"fmadd": (False, False), "fmsub": (False, True),
                        "fnmsub": (True, False),
                        "fnmadd": (True, True)}[mnem.split(".")[0]]

        def run():
            fr[rd], flags = f64_fma(fr[rs1], fr[rs2], fr[rs3],
                                    m.rounding(static_rm), neg_p, neg_c)
            m.fflags |= flags
            return nxt
        return run
    if kind == "fcvt_if":
        src = {"w": lambda v: sext(v, 32), "wu": lambda v: v & M32,
               "l": s64, "lu": lambda v: v}[mnem.split(".")[2]]

        def run():
            fr[rd], flags = f64_from_int(src(xr[rs1]), m.rounding(static_rm))
            m.fflags |= flags
            return nxt
        return run
    if kind == "fcvt_fi":
        lo, hi, bits = {"w": (-(1 << 31), (1 << 31) - 1, 32),
                        "wu": (0, M32, 32),
                        "l": (-(1 << 63), (1 << 63) - 1, 64),
                        "lu": (0, M64, 64)}[mnem.split(".")[1]]

        def run():
            n, flags = f64_to_int(fr[rs1], m.rounding(static_rm), lo, hi)
            xr[rd] = (sext(n, 32) if bits == 32 else n) & M64
            m.fflags |= flags
            return nxt
        return run
    if kind == "fmv_xf":
        def run():
            xr[rd] = fr[rs1]
            return nxt
        return run
    if kind == "fmv_fx":
        def run():
            fr[rd] = xr[rs1]
            return nxt
        return run
    if kind == "fsgnj":
        how = mnem.split(".")[0]

        def run():
            a, b = fr[rs1], fr[rs2]
            sign = (b if how == "fsgnj" else ~b if how == "fsgnjn"
                    else a ^ b) & SIGN
            fr[rd] = (a & MAG) | sign
            return nxt
        return run
    if kind == "fminmax":
        want_max = mnem.startswith("fmax")

        def run():
            fr[rd], flags = f64_minmax(fr[rs1], fr[rs2], want_max)
            m.fflags |= flags
            return nxt
        return run
    if kind == "fcmp":
        op = mnem.split(".")[0]

        def run():
            xr[rd], flags = f64_compare(fr[rs1], fr[rs2], op)
            m.fflags |= flags
            return nxt
        return run
    if kind == "fclass":
        def run():
            xr[rd] = f64_class(fr[rs1])
            return nxt
        return run
    return fail("not implemented")


# ---------------------------------------------------------------------------
# Running, listing, checking
# ---------------------------------------------------------------------------

def simulate(path, max_steps=MAX_STEPS):
    entry, segments, sections, info, problems = read_elf(path)
    m = Machine(entry, segments)
    m.run(max_steps)
    return m, (entry, segments, sections, info, problems)


def summarize(m):
    """Dynamic counts of a finished run."""
    by_mnem, by_class, checkable = {}, {}, 0
    for _fn, d, count in m.cache.values():
        if not count:
            continue
        by_mnem[d.mnem] = by_mnem.get(d.mnem, 0) + count
        by_class[d.opclass] = by_class.get(d.opclass, 0) + count
        # What the shadow-unit CPU checks: not a memory access, not
        # serializing, writes one int register other than x0 or one FP one.
        if (d.dest == "f" or (d.dest == "x" and d.rd != 0)) and d.kind not in (
                "load", "store", "fload", "fstore", "csr", "ecall"):
            checkable += count

    def ordered(counts):
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return {
        "dynamic_insts": sum(by_mnem.values()),
        "dynamic_by_mnemonic": ordered(by_mnem),
        "dynamic_by_opclass": ordered(by_class),
        "checkable_insts": checkable,
    }


def text_words(segment):
    data = segment.data[:segment.filesz]
    return [int.from_bytes(data[i:i + 4], "little")
            for i in range(0, len(data) - 3, 4)]


def normalize(text):
    return re.sub(r"\s*,\s*", ", ", " ".join(text.split()))


# "checksum: 0x" + 16 lowercase hex digits + "\n": 12 + 16 + 1 = 29 bytes
CHECKSUM_LINE = re.compile(rb"checksum: 0x[0-9a-f]{16}\n")
CHECKSUM_BYTES = 29
LST_LINE = re.compile(r"^\s*(?:0x)?([0-9a-fA-F]+)\s+(?:0x)?([0-9a-fA-F]{8})"
                      r"\s+(\S.*?)\s*$")


def check_program(name, directory, max_steps):
    """(manifest entry, problems) for one program."""
    path = os.path.join(directory, name)
    problems = []
    entry, segments, sections, info, elf_problems = read_elf(path)
    problems += elf_problems

    # The shape gen_tests.py promises: one R+X segment that is .text.
    if len(segments) != 1:
        problems.append(f"{len(segments)} PT_LOAD segments, expected 1")
    seg = segments[0]
    if seg.flags != 5:
        problems.append(f"segment flags {seg.flags:#x}, expected PF_R|PF_X")
    text = sections.get(".text")
    if text is None:
        problems.append("no .text section")
    elif (text["type"], text["flags"], text["addr"], text["offset"],
          text["size"]) != (1, 6, seg.start, seg.offset, seg.filesz):
        problems.append(f".text section {text} doesn't match the segment")
    if ".shstrtab" not in sections:
        problems.append("no .shstrtab section")
    if info["osabi"] != 0:
        problems.append(f"EI_OSABI is {info['osabi']}, expected 0")
    if info["e_flags"] != 0x4:
        problems.append(f"e_flags is {info['e_flags']:#x}, expected 0x4")
    if entry != seg.start:
        problems.append(f"entry {entry:#x} is not the start of .text")
    if seg.filesz % 4:
        problems.append("code size is not a multiple of 4")

    # Every word must match the listing, and decode to the listing's text.
    words = text_words(seg)
    listing = []
    with open(path + ".lst") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            mt = LST_LINE.match(line)
            if not mt:
                problems.append(f"{name}.lst:{lineno}: can't parse {line!r}")
                continue
            listing.append((int(mt.group(1), 16), int(mt.group(2), 16),
                            mt.group(3)))
    if len(listing) != len(words):
        problems.append(f"{name}.lst has {len(listing)} lines, the code has "
                        f"{len(words)} words")
    mismatches = 0
    for n, (addr, word, asm) in enumerate(listing):
        if addr != seg.start + 4 * n:
            problems.append(f"{name}.lst line {n + 1}: address {addr:#x}, "
                            f"expected {seg.start + 4 * n:#x}")
            continue
        if n >= len(words):
            break
        if words[n] != word:
            problems.append(f"{addr:#x}: the file has {words[n]:08x}, "
                            f"{name}.lst says {word:08x}")
        got = decode(words[n], addr).text
        if normalize(got) != normalize(asm):
            mismatches += 1
            problems.append(f"{addr:#x}: {words[n]:08x} decodes to '{got}', "
                            f"{name}.lst says '{asm}'")

    # Run it.
    m = Machine(entry, segments)
    try:
        m.run(max_steps)
    except SimError as e:
        problems.append(f"run failed: {e}")
        return None, problems
    out = bytes(m.stdout)
    if m.exit_code != 0:
        problems.append(f"exit code {m.exit_code}")
    if not CHECKSUM_LINE.fullmatch(out):
        problems.append(f"stdout is {out!r}, not one {CHECKSUM_BYTES}-byte "
                        "checksum line")
    if m.stderr:
        problems.append(f"stderr is {bytes(m.stderr)!r}")
    if [s["call"] for s in m.syscalls] != ["write", "exit"]:
        problems.append(f"syscalls {m.syscalls}, expected one write and exit")
    result = {
        "expected_stdout": out.decode("ascii", "replace"),
        "exit_code": m.exit_code,
        "static_insts": len(words),
    }
    result.update(summarize(m))
    result.update({
        "fflags_at_exit": flag_names(m.fflags),
        "text_bytes": seg.filesz,
        "entry": f"{entry:#x}",
        "listing_mismatches": mismatches,
    })
    return result, problems


def self_test():
    for word, want in DECODER_SELF_TEST.items():
        got = decode(word).text
        if got != want:
            raise SimError(f"decoder self-test: {word:#010x} -> {got!r}, "
                           f"expected {want!r}")
    # A few rounding cases with known answers.
    one, three = 0x3FF0000000000000, 0x4008000000000000
    third_rne = f64_div(one, three, RNE)[0]
    if third_rne != 0x3FD5555555555555 or f64_div(one, three, RUP)[0] != 0x3FD5555555555556:
        raise SimError("FP self-test: 1/3")
    if f64_add(0x4340000000000000, one, RNE)[0] != 0x4340000000000000:  # 2**53 + 1
        raise SimError("FP self-test: ties to even")
    if f64_to_int(0xC004000000000000, RTZ, -(1 << 63), (1 << 63) - 1) != (-2, NX):
        raise SimError("FP self-test: fcvt of -2.5 with rtz")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("programs", nargs="*", help="programs to run (or names "
                    "to check with --check)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="cross-check, run, and write the manifest")
    mode.add_argument("--disasm", action="store_true",
                      help="print rvsim's listing of each program")
    ap.add_argument("--dir", default=HERE,
                    help="directory of the programs for --check "
                         "(default: this script's)")
    ap.add_argument("--manifest",
                    help="manifest to write with --check "
                         "(default: DIR/manifest.json)")
    ap.add_argument("--max-steps", type=int, default=MAX_STEPS)
    args = ap.parse_args(argv)
    self_test()

    if args.disasm:
        for path in args.programs:
            entry, segments, _sections, _info, problems = read_elf(path)
            for p in problems:
                print(f"# {path}: {p}", file=sys.stderr)
            for seg in segments:
                if seg.flags & 1:
                    for n, word in enumerate(text_words(seg)):
                        pc = seg.start + 4 * n
                        print(f"{pc:08x}  {word:08x}  {decode(word, pc).text}")
        return 0

    if not args.check:
        if not args.programs:
            ap.error("give a program to run, or --check or --disasm")
        status = 0
        for path in args.programs:
            m, (_e, _s, _sec, _i, problems) = simulate(path, args.max_steps)
            sys.stdout.write(m.stdout.decode("ascii", "replace"))
            sys.stdout.flush()
            s = summarize(m)
            print(f"rvsim: {path}: exit {m.exit_code}, {s['dynamic_insts']} "
                  f"instructions, fflags '{flag_names(m.fflags)}'",
                  file=sys.stderr)
            for p in problems:
                print(f"rvsim: {path}: {p}", file=sys.stderr)
            status = status or (m.exit_code != 0)
        return status

    names = args.programs or PROGRAMS
    manifest_path = args.manifest or os.path.join(args.dir, "manifest.json")
    results, failed = {}, False
    for name in names:
        result, problems = check_program(name, args.dir, args.max_steps)
        for p in problems:
            print(f"rvsim: {name}: {p}", file=sys.stderr)
        if problems or result is None:
            failed = True
            print(f"{name:10s} FAILED ({len(problems)} problems)")
            continue
        results[name] = result
        print(f"{name:10s} ok  {result['static_insts']:4d} static "
              f"{result['dynamic_insts']:8d} dynamic  "
              f"{result['expected_stdout'].strip()}  exit {result['exit_code']}")
    if failed:
        return 1

    # Merge into the manifest, keeping anything else that is already there.
    try:
        with open(manifest_path) as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        manifest = {}
    programs = manifest.get("programs", {})
    for name, result in results.items():
        entry = programs.get(name, {})
        entry.update(result)
        programs[name] = entry
    order = [n for n in PROGRAMS if n in programs]
    order += sorted(n for n in programs if n not in PROGRAMS)
    manifest = {
        "description": (
            "Results of rvsim.py --check: what each program prints (one "
            "29-byte line), its exit code, and its static and dynamic "
            "instruction counts, by mnemonic and by gem5 O3 op class. "
            "checkable_insts counts the committed instructions that the "
            "shadow-unit CPU checks: not memory accesses, not serializing, "
            "and writing one integer register other than x0 or one FP "
            "register. The model entries come from gen_tests.py."),
        "programs": {n: programs[n] for n in order},
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SimError as e:
        print(f"rvsim: {e}", file=sys.stderr)
        sys.exit(2)
