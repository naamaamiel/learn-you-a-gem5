

import argparse
import json
import os
import random
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M64 = (1 << 64) - 1

TEXT_VADDR = 0x11000  # .text is mapped here, and it is the entry point
TEXT_OFFSET = 0x1000  # .text is stored here in the file (same offset mod 4 KiB)
PAGE = 0x1000

# The loop branch of kernel. The convention is "bne x31, x0, loop", and the
# four microbenchmarks use it. kernel is the program that runs with faults
# and no shadow unit, though, and a committed fault that flips bit 63 of x31
# would send a bne loop around about 2**63 more times. "blt x0, x31, loop"
# (loop while x31 > 0) executes exactly the same instructions, but a flipped
# counter ends the loop early instead. Set this to "bne" for the convention.
KERNEL_LOOP_BRANCH = "blt"

# Instructions in each microbenchmark's chain per iteration. Two more (addi,
# bne) end each iteration, so CPI comes out at UNROLL / (UNROLL + 2) = 0.97
# times the chain's latency per instruction, and indep_add's IPC 1.03 times
# its chain-bound value.
UNROLL = 64


# ---------------------------------------------------------------------------
# Instruction encoding: exactly the instructions these programs use.
# ---------------------------------------------------------------------------

OP, OP_IMM, OP_IMM_32 = 0b0110011, 0b0010011, 0b0011011
LUI, STORE, BRANCH = 0b0110111, 0b0100011, 0b1100011
SYSTEM, OP_FP = 0b1110011, 0b1010011

R_INT = {  # mnemonic: (funct7, funct3); opcode OP
    "add": (0b0000000, 0b000),
    "xor": (0b0000000, 0b100),
    "mul": (0b0000001, 0b000),
    "div": (0b0000001, 0b100),
}
I_INT = {  # mnemonic: (opcode, funct3)
    "addi": (OP_IMM, 0b000),
    "slti": (OP_IMM, 0b010),
    "andi": (OP_IMM, 0b111),
    "addiw": (OP_IMM_32, 0b000),
}
SHIFT_IMM = {  # mnemonic: (imm[11:6], funct3); opcode OP_IMM, 6-bit shamt (RV64)
    "slli": (0b000000, 0b001),
    "srli": (0b000000, 0b101),
}
STORES = {"sb": 0b000}  # funct3; opcode STORE
BRANCHES = {"bne": 0b001, "blt": 0b100}  # funct3; opcode BRANCH
FP_ARITH = {  # mnemonic: funct7 = funct5 << 2 | fmt (D = 01); opcode OP_FP, funct3 = rm
    "fadd.d": 0b0000001,
    "fmul.d": 0b0001001,
}
FP_CONVERT = {  # mnemonic: (funct7, rs2 field, rd file, rs1 file); funct3 = rm
    "fcvt.d.l": (0b1101001, 0b00010, "f", "x"),
    "fcvt.l.d": (0b1100001, 0b00010, "x", "f"),
}
FP_MOVE = {  # mnemonic: (funct7, rd file, rs1 file); rs2 = 0, funct3 = 000
    "fmv.x.d": (0b1110001, "x", "f"),
    "fmv.d.x": (0b1111001, "f", "x"),
}
ROUNDING = {"rne": 0b000, "rtz": 0b001, "rdn": 0b010, "rup": 0b011, "rmm": 0b100}


def reg(name, regfile):
    """The number of register name ('x5' or 'f5'), which must be in regfile."""
    if not (isinstance(name, str) and name[:1] == regfile
            and name[1:].isdigit() and int(name[1:]) < 32):
        raise ValueError(f"expected an {regfile} register, got {name!r}")
    return int(name[1:])


def field(value, bits, what):
    """value as a bits-wide two's-complement field."""
    if not -(1 << (bits - 1)) <= value < 1 << (bits - 1):
        raise ValueError(f"{what} {value} doesn't fit in {bits} signed bits")
    return value & ((1 << bits) - 1)


def r_type(funct7, rs2, rs1, funct3, rd, opcode):
    return funct7 << 25 | rs2 << 20 | rs1 << 15 | funct3 << 12 | rd << 7 | opcode


def i_type(imm, rs1, funct3, rd, opcode):
    imm = field(imm, 12, "I-immediate")
    return imm << 20 | rs1 << 15 | funct3 << 12 | rd << 7 | opcode


def s_type(imm, rs2, rs1, funct3, opcode):
    imm = field(imm, 12, "S-immediate")
    return ((imm >> 5) << 25 | rs2 << 20 | rs1 << 15 | funct3 << 12
            | (imm & 0x1F) << 7 | opcode)


def b_type(offset, rs2, rs1, funct3, opcode):
    if offset % 2:
        raise ValueError(f"odd branch offset {offset}")
    imm = field(offset, 13, "branch offset")
    return (((imm >> 12) & 1) << 31 | ((imm >> 5) & 0x3F) << 25 | rs2 << 20
            | rs1 << 15 | funct3 << 12 | ((imm >> 1) & 0xF) << 8
            | ((imm >> 11) & 1) << 7 | opcode)


def u_type(imm20, rd, opcode):
    if not 0 <= imm20 < 1 << 20:
        raise ValueError(f"U-immediate {imm20:#x} doesn't fit in 20 bits")
    return imm20 << 12 | rd << 7 | opcode


def encode(mnem, ops, pc, labels):
    """(word, assembly text) of one instruction at address pc."""
    if mnem in R_INT:
        rd, rs1, rs2 = ops
        funct7, funct3 = R_INT[mnem]
        word = r_type(funct7, reg(rs2, "x"), reg(rs1, "x"), funct3,
                      reg(rd, "x"), OP)
        return word, f"{mnem} {rd}, {rs1}, {rs2}"
    if mnem in I_INT:
        rd, rs1, imm = ops
        opcode, funct3 = I_INT[mnem]
        word = i_type(imm, reg(rs1, "x"), funct3, reg(rd, "x"), opcode)
        return word, f"{mnem} {rd}, {rs1}, {imm}"
    if mnem in SHIFT_IMM:
        rd, rs1, shamt = ops
        if not 0 <= shamt < 64:
            raise ValueError(f"shift amount {shamt}")
        top, funct3 = SHIFT_IMM[mnem]
        word = ((top << 6 | shamt) << 20 | reg(rs1, "x") << 15 | funct3 << 12
                | reg(rd, "x") << 7 | OP_IMM)
        return word, f"{mnem} {rd}, {rs1}, {shamt}"
    if mnem == "lui":
        rd, imm20 = ops
        return u_type(imm20, reg(rd, "x"), LUI), f"lui {rd}, {imm20:#x}"
    if mnem in STORES:
        rs2, offset, base = ops  # sb rs2, offset(base)
        word = s_type(offset, reg(rs2, "x"), reg(base, "x"), STORES[mnem],
                      STORE)
        return word, f"{mnem} {rs2}, {offset}({base})"
    if mnem in BRANCHES:
        rs1, rs2, label = ops
        offset = labels[label] - pc  # relative to the branch itself
        word = b_type(offset, reg(rs2, "x"), reg(rs1, "x"), BRANCHES[mnem],
                      BRANCH)
        return word, f"{mnem} {rs1}, {rs2}, {offset}"
    if mnem == "ecall":
        if ops:
            raise ValueError("ecall takes no operands")
        return SYSTEM, "ecall"  # every other field is zero
    if mnem in FP_ARITH:
        rd, rs1, rs2, rm = ops
        word = r_type(FP_ARITH[mnem], reg(rs2, "f"), reg(rs1, "f"),
                      ROUNDING[rm], reg(rd, "f"), OP_FP)
        return word, f"{mnem} {rd}, {rs1}, {rs2}, {rm}"
    if mnem in FP_CONVERT:
        rd, rs1, rm = ops
        funct7, rs2_field, rd_file, rs1_file = FP_CONVERT[mnem]
        word = r_type(funct7, rs2_field, reg(rs1, rs1_file), ROUNDING[rm],
                      reg(rd, rd_file), OP_FP)
        return word, f"{mnem} {rd}, {rs1}, {rm}"
    if mnem in FP_MOVE:
        rd, rs1 = ops
        funct7, rd_file, rs1_file = FP_MOVE[mnem]
        word = r_type(funct7, 0, reg(rs1, rs1_file), 0b000, reg(rd, rd_file),
                      OP_FP)
        return word, f"{mnem} {rd}, {rs1}"
    raise ValueError(f"no encoding for {mnem!r}")


# ---------------------------------------------------------------------------
# The li pseudo-instruction
# ---------------------------------------------------------------------------

def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def li_sequence(rd, value):
    """The instructions of "li rd, value", for any 64-bit value.

    Like the GNU and LLVM expansion: addi for a 12-bit value, lui (+ addiw)
    for a 32-bit one, and otherwise li of the upper bits, slli, and addi of
    the low 12 bits. addi sign-extends its immediate, so the low 12 bits are
    taken as a signed number and the upper bits absorb the borrow.
    """
    v = sext(value, 64)
    if -2048 <= v < 2048:
        return [("addi", (rd, "x0", v))]
    lo = sext(v, 12)
    if -(1 << 31) <= v < 1 << 31:
        # lui sign-extends from bit 31, and addiw wraps at 32 bits, so a
        # value just below 2**31 still comes out right: lui 0x80000, addiw -1.
        seq = [("lui", (rd, ((v - lo) >> 12) & 0xFFFFF))]
        if lo:
            seq.append(("addiw", (rd, rd, lo)))
        return seq
    hi, shift = (v - lo) >> 12, 12
    while not hi & 1:
        hi, shift = hi >> 1, shift + 1
    seq = li_sequence(rd, hi) + [("slli", (rd, rd, shift))]
    if lo:
        seq.append(("addi", (rd, rd, lo)))
    return seq


def eval_li(seq):
    """The value a li sequence leaves in its register (RV64 semantics)."""
    r = 0
    for mnem, ops in seq:
        if mnem == "addi":
            r = ((0 if ops[1] == "x0" else r) + ops[2]) & M64
        elif mnem == "lui":
            r = sext(ops[1] << 12, 32) & M64
        elif mnem == "addiw":
            r = sext(r + ops[2], 32) & M64
        elif mnem == "slli":
            r = (r << ops[2]) & M64
        else:
            raise ValueError(mnem)
    return r


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------

class Program:
    def __init__(self, name):
        self.name = name
        self.insts = []  # (mnemonic, operands)
        self.labels = {}

    def here(self):
        return TEXT_VADDR + 4 * len(self.insts)

    def label(self, name):
        if name in self.labels:
            raise ValueError(f"label {name} defined twice")
        self.labels[name] = self.here()

    def op(self, mnem, *ops):
        self.insts.append((mnem, ops))

    def li(self, rd, value):
        seq = li_sequence(rd, value)
        if eval_li(seq) != value & M64:
            raise AssertionError(f"li {rd}, {value:#x} expands wrongly: {seq}")
        for mnem, ops in seq:
            self.op(mnem, *ops)

    def assemble(self):
        """(code bytes, listing lines)."""
        words, lines = [], []
        for n, (mnem, ops) in enumerate(self.insts):
            pc = TEXT_VADDR + 4 * n
            word, text = encode(mnem, ops, pc, self.labels)
            words.append(word)
            lines.append(f"{pc:08x}  {word:08x}  {text}")
        return struct.pack(f"<{len(words)}I", *words), lines


def loop_top(p, iterations):
    p.li("x31", iterations)
    p.label("loop")


def loop_bottom(p, branch="bne"):
    p.op("addi", "x31", "x31", -1)
    if branch == "bne":
        p.op("bne", "x31", "x0", "loop")
    elif branch == "blt":
        p.op("blt", "x0", "x31", "loop")  # while x31 > 0
    else:
        raise ValueError(branch)
    p.label("after_loop")


PREFIX = "checksum: 0x"
LINE_BYTES = len(PREFIX) + 16 + 1  # 29: the prefix, 16 hex digits, "\n"
WARM_FLAG = "x27"  # 1 during the warm-up pass, 0 after it


def warm_up(p):
    """The first two instructions: run the print code without printing.

    print_checksum_and_exit() skips the write and the exit while WARM_FLAG
    is set, and branches back to "start".
    """
    p.op("addi", WARM_FLAG, "x0", 1)
    p.op("bne", WARM_FLAG, "x0", "print")
    p.label("start")


def print_checksum_and_exit(p):
    """Print "checksum: 0x%016x\\n" % x10 with write(1, sp, 29), then exit(0).

    Straight-line code: the hex digits come from shifts and masks, not a
    loop, and no register but sp holds an address. In the warm-up pass, it
    builds the string, skips the write and the exit, and goes back to the
    start of the program with WARM_FLAG cleared.
    """
    p.label("print")
    p.op("addi", "x2", "x2", -64)
    for i, ch in enumerate(PREFIX):
        p.op("addi", "x5", "x0", ord(ch))
        p.op("sb", "x5", i, "x2")
    for i in range(16):  # most significant nibble first
        shift = 60 - 4 * i
        if shift:
            p.op("srli", "x6", "x10", shift)
            p.op("andi", "x6", "x6", 15)
        else:
            p.op("andi", "x6", "x10", 15)
        p.op("slti", "x7", "x6", 10)     # 1 for 0-9, 0 for 10-15
        p.op("addi", "x7", "x7", -1)     # 0 or -1
        p.op("andi", "x7", "x7", 39)     # 0 or 'a' - '0' - 10
        p.op("add", "x6", "x6", "x7")
        p.op("addi", "x6", "x6", ord("0"))
        p.op("sb", "x6", len(PREFIX) + i, "x2")
    p.op("addi", "x5", "x0", ord("\n"))
    p.op("sb", "x5", LINE_BYTES - 1, "x2")
    p.op("addi", "x17", "x0", 64)        # write(1, sp, 29)
    p.op("addi", "x10", "x0", 1)
    p.op("addi", "x11", "x2", 0)
    p.op("addi", "x12", "x0", LINE_BYTES)
    p.op("bne", WARM_FLAG, "x0", "warmed_up")  # warm-up pass: don't print
    p.label("print_end")
    p.op("ecall")
    p.op("addi", "x17", "x0", 93)        # exit(0)
    p.op("addi", "x10", "x0", 0)
    p.op("ecall")
    p.label("warmed_up")
    p.op("addi", "x2", "x2", 64)
    p.op("addi", WARM_FLAG, "x0", 0)
    p.op("bne", "x10", "x0", "start")    # x10 is 1 here: always taken


def rv_div(a, b):
    """RISC-V div of two 64-bit register values."""
    a, b = sext(a, 64), sext(b, 64)
    if b == 0:
        return M64
    if a == -(1 << 63) and b == -1:
        return a & M64
    q = abs(a) // abs(b)
    return (-q if (a < 0) != (b < 0) else q) & M64


def f64_bits(value):
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def chain_add():
    """x5 += x6 (x6 = 1): one chain of UNROLL dependent adds per iteration."""
    n = 20000
    p = Program("chain_add")
    warm_up(p)
    p.li("x5", 0)
    p.li("x6", 1)
    loop_top(p, n)
    for _ in range(UNROLL):
        p.op("add", "x5", "x5", "x6")
    loop_bottom(p)
    p.op("addi", "x10", "x5", 0)
    print_checksum_and_exit(p)

    x5 = 0
    for _ in range(UNROLL * n):
        x5 = (x5 + 1) & M64
    return p, n, x5


MUL_FACTOR = 0x9E3779B97F4A7C15  # odd, so the product never goes to 0


def chain_mul():
    """x5 *= x6: one chain of UNROLL dependent muls per iteration."""
    n = 4000
    p = Program("chain_mul")
    warm_up(p)
    p.li("x5", 3)
    p.li("x6", MUL_FACTOR)
    loop_top(p, n)
    for _ in range(UNROLL):
        p.op("mul", "x5", "x5", "x6")
    loop_bottom(p)
    p.op("addi", "x10", "x5", 0)
    print_checksum_and_exit(p)

    x5 = 3
    for _ in range(UNROLL * n):
        x5 = (x5 * MUL_FACTOR) & M64
    return p, n, x5


DIV_START = 0x0123456789ABCDEF


def chain_div():
    """x5 /= x6 (x6 = 1): one chain of UNROLL dependent divs per iteration."""
    n = 800
    p = Program("chain_div")
    warm_up(p)
    p.li("x5", DIV_START)
    p.li("x6", 1)
    loop_top(p, n)
    for _ in range(UNROLL):
        p.op("div", "x5", "x5", "x6")
    loop_bottom(p)
    p.op("addi", "x10", "x5", 0)
    print_checksum_and_exit(p)

    x5 = DIV_START
    for _ in range(UNROLL * n):
        x5 = rv_div(x5, 1)
    return p, n, x5


def indep_add():
    """Eight independent add chains, x5..x12 += x13 (x13 = 1), interleaved
    round-robin so that consecutive adds never depend on each other: UNROLL
    adds per iteration, UNROLL / 8 on each chain."""
    n = 20000
    chains = [f"x{r}" for r in range(5, 13)]
    p = Program("indep_add")
    warm_up(p)
    for r in chains:
        p.li(r, 0)
    p.li("x13", 1)
    loop_top(p, n)
    for _ in range(UNROLL // 8):
        for r in chains:
            p.op("add", r, r, "x13")
    loop_bottom(p)
    # Sum the chains into x14 first: x10 is one of them.
    p.op("add", "x14", "x5", "x6")
    for r in chains[2:]:
        p.op("add", "x14", "x14", r)
    p.op("addi", "x10", "x14", 0)
    print_checksum_and_exit(p)

    vals = [0] * 8
    for _ in range(n):
        for _ in range(UNROLL // 8):
            for c in range(8):
                vals[c] = (vals[c] + 1) & M64
    return p, n, sum(vals) & M64


LCG_A = 6364136223846793005
LCG_C = 1442695040888963407
KERNEL_SEED = 0x0123456789ABCDEF


def kernel():
    """A mixed integer and floating-point loop whose checksum depends on every
    result. Per iteration (29 instructions):

        x   = x * A + C                    mul, add                IntMult, IntAlu
        q   = x / 7  (signed)              div                     IntDiv
        w   = w * A + q                    mul, add                IntMult, IntAlu
        g   = (double)(x >> 11) * 2**-53   srli, fcvt.d.l, fmul.d  exact, in [0, 1)
        f   = f * 0.5 + 1.0 + g            fmul.d, fadd.d, fadd.d  stays in [1, 4)
        s   = s + f                        fadd.d                  running sum
        c   = (long)(f * 1000.0)           fmul.d, fcvt.l.d (rtz)
        acc ^= x; acc += w; acc ^= c; acc += bits(f); acc ^= bits(s)    fmv.x.d x2
        acc ^= acc << 13; acc ^= acc >> 7; acc ^= acc << 17      xorshift64
        addi x31, x31, -1; blt x0, x31, loop

    Registers: x5 x, x6 A, x7 C, x8 acc, x9 7, x18 w, x28-x30 temporaries;
    f0 f, f1 0.5, f2 1.0, f3 1000.0, f4 2**-53, f5 g, f6 f*1000, f7 s.
    Every update of acc is a bijection of acc, so a wrong value anywhere stays
    in acc to the end; q and the FP bits mix it nonlinearly. The loop has no
    loads or stores, and no FP exception but inexact can happen: even with a
    sign flipped anywhere, every FP value stays finite.
    """
    n = 20000
    p = Program("kernel")
    warm_up(p)
    p.li("x5", KERNEL_SEED)  # x
    p.li("x6", LCG_A)
    p.li("x7", LCG_C)
    p.li("x8", 0)  # acc
    p.li("x9", 7)
    p.li("x18", 0)  # w
    p.li("x28", f64_bits(1.0))
    p.op("fmv.d.x", "f0", "x28")  # f = 1.0
    p.op("fmv.d.x", "f2", "x28")  # 1.0
    p.li("x28", f64_bits(0.5))
    p.op("fmv.d.x", "f1", "x28")
    p.li("x28", f64_bits(1000.0))
    p.op("fmv.d.x", "f3", "x28")
    p.li("x28", f64_bits(2.0 ** -53))
    p.op("fmv.d.x", "f4", "x28")
    p.op("fmv.d.x", "f7", "x0")  # s = 0.0
    loop_top(p, n)
    p.op("mul", "x5", "x5", "x6")
    p.op("add", "x5", "x5", "x7")
    p.op("div", "x28", "x5", "x9")
    p.op("mul", "x18", "x18", "x6")
    p.op("add", "x18", "x18", "x28")
    p.op("srli", "x29", "x5", 11)
    p.op("fcvt.d.l", "f5", "x29", "rne")
    p.op("fmul.d", "f5", "f5", "f4", "rne")
    p.op("fmul.d", "f0", "f0", "f1", "rne")
    p.op("fadd.d", "f0", "f0", "f2", "rne")
    p.op("fadd.d", "f0", "f0", "f5", "rne")
    p.op("fadd.d", "f7", "f7", "f0", "rne")
    p.op("fmul.d", "f6", "f0", "f3", "rne")
    p.op("fcvt.l.d", "x30", "f6", "rtz")
    p.op("fmv.x.d", "x29", "f0")
    p.op("fmv.x.d", "x28", "f7")
    p.op("xor", "x8", "x8", "x5")
    p.op("add", "x8", "x8", "x18")
    p.op("xor", "x8", "x8", "x30")
    p.op("add", "x8", "x8", "x29")
    p.op("xor", "x8", "x8", "x28")
    for shift_op, k in (("slli", 13), ("srli", 7), ("slli", 17)):
        p.op(shift_op, "x28", "x8", k)
        p.op("xor", "x8", "x8", "x28")
    loop_bottom(p, KERNEL_LOOP_BRANCH)
    p.op("addi", "x10", "x8", 0)
    print_checksum_and_exit(p)

    # The model: the same computation with Python ints and IEEE doubles.
    x, w, acc, f, s = KERNEL_SEED, 0, 0, 1.0, 0.0
    for _ in range(n):
        x = (x * LCG_A + LCG_C) & M64
        q = rv_div(x, 7)
        w = (w * LCG_A + q) & M64
        g = float(x >> 11) * 2.0 ** -53
        f = f * 0.5
        f = f + 1.0
        f = f + g
        s = s + f
        c = int(f * 1000.0) & M64  # int() truncates toward zero, like rtz
        acc ^= x
        acc = (acc + w) & M64
        acc ^= c
        acc = (acc + f64_bits(f)) & M64
        acc ^= f64_bits(s)
        acc ^= (acc << 13) & M64
        acc ^= acc >> 7
        acc ^= (acc << 17) & M64
    return p, n, acc


PROGRAMS = [chain_add, chain_mul, chain_div, indep_add, kernel]


# ---------------------------------------------------------------------------
# ELF output
# ---------------------------------------------------------------------------

def write_elf(path, code):
    """A static ET_EXEC with one PT_LOAD (R+X) segment that holds the code.

    gem5 v25's loader places a segment at p_paddr, picks Linux for an unknown
    OS ABI, and walks the section headers through e_shstrndx, so p_paddr =
    p_vaddr, EI_OSABI = 0, and there are three sections: null, .text and
    .shstrtab.
    """
    assert TEXT_OFFSET % PAGE == TEXT_VADDR % PAGE
    shstrtab = b"\0.text\0.shstrtab\0"  # .text at 1, .shstrtab at 7
    shstrtab_offset = TEXT_OFFSET + len(code)
    shoff = (shstrtab_offset + len(shstrtab) + 7) & ~7
    ident = b"\x7fELF" + bytes([
        2,  # EI_CLASS: ELFCLASS64
        1,  # EI_DATA: ELFDATA2LSB
        1,  # EI_VERSION: EV_CURRENT
        0,  # EI_OSABI: ELFOSABI_NONE
        0,  # EI_ABIVERSION
    ]) + bytes(7)
    ehdr = struct.pack(
        "<16sHHIQQQIHHHHHH", ident,
        2,           # e_type: ET_EXEC
        243,         # e_machine: EM_RISCV
        1,           # e_version
        TEXT_VADDR,  # e_entry
        64,          # e_phoff
        shoff,       # e_shoff
        0x4,         # e_flags: EF_RISCV_FLOAT_ABI_DOUBLE, no EF_RISCV_RVC
        64, 56, 1,   # e_ehsize, e_phentsize, e_phnum
        64, 3, 2)    # e_shentsize, e_shnum, e_shstrndx
    phdr = struct.pack(
        "<IIQQQQQQ",
        1,           # p_type: PT_LOAD
        4 | 1,       # p_flags: PF_R | PF_X
        TEXT_OFFSET, TEXT_VADDR, TEXT_VADDR,  # p_offset, p_vaddr, p_paddr
        len(code), len(code),                 # p_filesz, p_memsz
        PAGE)        # p_align
    shdrs = bytes(64) + struct.pack(
        "<IIQQQQIIQQ",
        1, 1, 2 | 4,  # .text: SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR
        TEXT_VADDR, TEXT_OFFSET, len(code), 0, 0, 4, 0) + struct.pack(
        "<IIQQQQIIQQ",
        7, 3, 0,      # .shstrtab: SHT_STRTAB
        0, shstrtab_offset, len(shstrtab), 0, 0, 1, 0)
    image = bytearray(shoff + len(shdrs))
    image[0:64] = ehdr
    image[64:64 + 56] = phdr
    image[TEXT_OFFSET:TEXT_OFFSET + len(code)] = code
    image[shstrtab_offset:shstrtab_offset + len(shstrtab)] = shstrtab
    image[shoff:] = shdrs
    with open(path, "wb") as fh:
        fh.write(image)
    os.chmod(path, 0o755)


# ---------------------------------------------------------------------------
# Self-test and main
# ---------------------------------------------------------------------------

# A few encodings from the RISC-V manual's tables, as GNU objdump shows them.
KNOWN_WORDS = [
    ("addi", ("x17", "x0", 93), 0x05D00893),  # li a7, 93
    ("addi", ("x0", "x0", 0), 0x00000013),    # nop
    ("ecall", (), 0x00000073),
    ("mul", ("x10", "x10", "x11"), 0x02B50533),
    ("div", ("x10", "x10", "x11"), 0x02B54533),
    ("lui", ("x10", 0x12345), 0x12345537),
    ("sb", ("x10", 0, "x2"), 0x00A10023),
    ("fmv.x.d", ("x10", "f10"), 0xE2050553),
    ("fmv.d.x", ("f10", "x10"), 0xF2050553),
    ("fcvt.l.d", ("x10", "f10", "rtz"), 0xC2251553),
]


def self_test():
    for mnem, ops, want in KNOWN_WORDS:
        got = encode(mnem, ops, 0, {})[0]
        if got != want:
            raise AssertionError(f"{mnem} {ops}: {got:#010x}, want {want:#010x}")
    # bne x10, x0, -4 (a branch to the previous instruction)
    got = encode("bne", ("x10", "x0", "L"), 0x104, {"L": 0x100})[0]
    if got != 0xFE051EE3:
        raise AssertionError(f"bne: {got:#010x}")
    rng = random.Random(1)
    values = [0, 1, -1, 2047, 2048, -2048, -2049, 4095, 4096, 0x7FF, 0x800,
              0x7FFFF800, 0x7FFFFFFF, 0x80000000, -0x80000000, -0x80000001,
              0xFFFFFFFF, 0x100000000, 0x7FFFFFFFFFFFFFFF, 1 << 63, M64,
              MUL_FACTOR, DIV_START, LCG_A, LCG_C, f64_bits(1000.0)]
    values += [rng.getrandbits(64) for _ in range(5000)]
    values += [rng.getrandbits(rng.randint(1, 64)) for _ in range(5000)]
    for v in values:
        seq = li_sequence("x5", v)
        if eval_li(seq) != v & M64:
            raise AssertionError(f"li {v:#x}: {seq}")
        if len(seq) > 8:
            raise AssertionError(f"li {v:#x} takes {len(seq)} instructions")
        for mnem, ops in seq:
            encode(mnem, ops, 0, {})  # every immediate must fit its field


def main():
    ap = argparse.ArgumentParser(
        description="Write the Assignment 2 test programs, then check them "
                    "with rvsim.py.")
    ap.add_argument("--no-check", action="store_true",
                    help="only write the programs and listings")
    args = ap.parse_args()

    self_test()
    built = {}
    for build in PROGRAMS:
        p, iterations, checksum = build()
        code, lines = p.assemble()
        path = os.path.join(HERE, p.name)
        write_elf(path, code)
        with open(path + ".lst", "w") as fh:
            fh.write("\n".join(lines) + "\n")
        loop_insts = (p.labels["after_loop"] - p.labels["loop"]) // 4
        built[p.name] = {
            "checksum": checksum,
            "iterations": iterations,
            "loop_insts": loop_insts,
            "static_insts": len(lines),
            # Everything but the loop is straight-line code that runs once,
            # except that the warm-up pass runs the print code up to its
            # write once more.
            "dynamic_insts": len(lines) + (iterations - 1) * loop_insts
                             + (p.labels["print_end"] - p.labels["print"]) // 4,
        }
        print(f"{p.name:10s} {len(lines):4d} instructions, {iterations} x "
              f"{loop_insts}-instruction loop, model checksum 0x{checksum:016x}")
    if args.no_check:
        return 0

    manifest_path = os.path.join(HERE, "manifest.json")
    rvsim = os.path.join(HERE, "rvsim.py")
    r = subprocess.run([sys.executable, "-I", rvsim, "--check", "--dir", HERE,
                        "--manifest", manifest_path, *built])
    if r.returncode:
        print("gen_tests: rvsim.py --check failed", file=sys.stderr)
        return 1

    with open(manifest_path) as fh:
        manifest = json.load(fh)
    failures = 0
    for name, b in built.items():
        got = manifest["programs"][name]
        want_stdout = f"checksum: 0x{b['checksum']:016x}\n"
        for ok, what in [
            (got["expected_stdout"] == want_stdout,
             f"stdout {got['expected_stdout']!r}, model says {want_stdout!r}"),
            (got["dynamic_insts"] == b["dynamic_insts"],
             f"{got['dynamic_insts']} dynamic instructions, expected "
             f"{b['dynamic_insts']}"),
            (got["static_insts"] == b["static_insts"],
             f"{got['static_insts']} static instructions, expected "
             f"{b['static_insts']}"),
        ]:
            if not ok:
                failures += 1
                print(f"gen_tests: {name}: {what}", file=sys.stderr)
        got["model"] = {
            "checksum": f"0x{b['checksum']:016x}",
            "iterations": b["iterations"],
            "loop_insts": b["loop_insts"],
            "dynamic_insts": b["dynamic_insts"],
        }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    if failures:
        return 1
    print("gen_tests: rvsim agrees with the models on all programs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
