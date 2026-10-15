import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from capstone import *

SO_PATH = r'C:\FL26_Mod\recon\02_engine\il2cpp\libil2cpp.so'

# ELF parsing to find the .text section and load address
with open(SO_PATH, 'rb') as f:
    data = f.read()

# Parse ELF header
e_shoff = struct.unpack_from('<Q', data, 0x28)[0]  # section header offset
e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]

# Find .text section
text_offset = 0
text_vaddr = 0
text_size = 0
for i in range(e_shnum):
    sh = e_shoff + i * e_shentsize
    sh_type = struct.unpack_from('<I', data, sh + 4)[0]
    sh_addr = struct.unpack_from('<Q', data, sh + 16)[0]
    sh_offset = struct.unpack_from('<Q', data, sh + 24)[0]
    sh_size = struct.unpack_from('<Q', data, sh + 32)[0]
    # SHT_PROGBITS = 1, executable sections typically have SHF_EXECINSTR
    sh_flags = struct.unpack_from('<Q', data, sh + 8)[0]
    if sh_flags & 0x4 and sh_size > 1000000:  # SHF_EXECINSTR, large section = .text
        text_offset = sh_offset
        text_vaddr = sh_addr
        text_size = sh_size
        break

print(f'.text: file_offset=0x{text_offset:x}, vaddr=0x{text_vaddr:x}, size=0x{text_size:x}')

def rva_to_offset(rva):
    return text_offset + (rva - text_vaddr)

# Disassemble methods
methods = {
    'CalculateImageSavePath(ExternalDataArchives)': 0xD65A58,
    'CalculateKey(ExternalDataArchives)': 0xD659E8,
    'CalculateImageSavePath(ExternalDataAgent)': 0xD63750,
    'LoadFromFile(ExternalDataArchives)': 0xD65248,
    'SaveToFile(ExternalDataArchives)': 0xD64F94,
}

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

out = []
for name, rva in methods.items():
    offset = rva_to_offset(rva)
    if offset < 0 or offset >= len(data):
        out.append(f'\n=== {name} @ RVA 0x{rva:x} === OFFSET OUT OF RANGE')
        continue
    
    # Read 512 bytes for disassembly (should cover most methods)
    code = data[offset:offset+512]
    
    out.append(f'\n=== {name} @ RVA 0x{rva:x} (file offset 0x{offset:x}) ===')
    
    # Disassemble
    count = 0
    for insn in md.disasm(code, rva):
        out.append(f'  0x{insn.address:x}: {insn.mnemonic:10s} {insn.op_str}')
        count += 1
        # Stop at return or after 80 instructions
        if insn.mnemonic == 'ret' or count > 80:
            break

result = '\n'.join(out)
with open(r'C:\FL26_Mod\saves\disasm_paths.txt', 'w', encoding='utf-8') as f:
    f.write(result)
print(f'wrote {len(out)} lines')
# Print first method
for line in out[:30]:
    print(line)
