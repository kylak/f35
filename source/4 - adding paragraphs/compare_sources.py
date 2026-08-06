import sys, re, os, glob
sys.path.insert(0, "/home/gustav/f35/F35_MES_pipeline/source/4 - adding paragraphs")
import add_paragraphs as ap
import xml.etree.ElementTree as ET

BOOKS = {40:"MAT",41:"MRK",42:"LUK",43:"JHN",44:"ACT",45:"ROM",46:"1CO",47:"2CO",48:"GAL",49:"EPH",50:"PHP",51:"COL",52:"1TH",53:"2TH",54:"1TI",55:"2TI",56:"TIT",57:"PHM",58:"HEB",59:"JAS",60:"1PE",61:"2PE",62:"1JN",63:"2JN",64:"3JN",65:"JUD",66:"REV"}
USFM_BOOK_FILES = {}
for f in sorted(glob.glob("/tmp/opencode/f35_sources/usfm/*-*grcf35.usfm")):
    m = re.match(r"(\d+)-.*grcf35\.usfm$", os.path.basename(f))
    if m and 46 <= int(m.group(1)) <= 72:
        USFM_BOOK_FILES[int(m.group(1))-6] = f

tree = ET.parse("/tmp/opencode/f35_usfx/grcf35_usfx.xml")
USFX_BOOKS = {b.get("id"): b for b in tree.getroot().findall("book")}
PARA_STYLES = {"p","m","mi","pc","pi"}
HEAD_STYLES = {"ms","s1","s2","s3","mt","mt1","mt2","mt3","mt4","h","toc","ip","is","ili","imi","im","ib","id","fv"}

def usfx_chapter_data(bid, ch):
    book = USFX_BOOKS.get(bid)
    if book is None: return None
    rough, offs, cur_ch = [], [], None
    def add(s):
        for cc in s:
            rc = ap.rough_char(cc)
            if rc: rough.append(rc)
    def walk(node):
        if node.text: add(node.text)
        for c in node:
            if c.tag == "f":
                if c.tail: add(c.tail)
                continue
            walk(c)
            if c.tail: add(c.tail)
    for el in book:
        if el.tag == "c":
            cur_ch = int(el.get("id")); continue
        if el.tag != "p" or cur_ch != ch: continue
        st = el.get("style")
        if st in HEAD_STYLES: continue
        if st in PARA_STYLES: offs.append(len(rough))
        walk(el)
    return "".join(rough), offs

XETEX_DIR = "/tmp/opencode/f35_xetex"
PARA_MACROS = {"PP","MM","MI","PC","PI"}
HEAD_MACROS = {"SH","SHB","SHC","MS","MT","MTC","MTD","MTB","IB","IM","IMI","IP","ILI","IS"}

def skip_balanced(s, i):
    d = 0
    while i < len(s):
        if s[i] == "{": d += 1
        elif s[i] == "}":
            d -= 1
            if d == 0: return i+1
        i += 1
    return i

def parse_seg(seg):
    rough, offs, j = [], [], 0
    while j < len(seg):
        c = seg[j]
        if c == "\\":
            m2 = re.match(r"\\([A-Za-z]+)", seg[j:])
            if m2:
                name, k = m2.group(1), j + m2.end()
                if name in PARA_MACROS:
                    offs.append(len(rough)); j = k; continue
                if name in HEAD_MACROS:
                    k2 = seg.find("\\par", k)
                    j = k2 if k2 >= 0 else len(seg); continue
                if name == "FTNT":
                    j = k
                    for _ in range(2):
                        while j < len(seg) and seg[j] != "{": j += 1
                        j = skip_balanced(seg, j)
                    continue
                if name in ("VS","VerseOne"):
                    k2 = seg.find("}", j)
                    j = k2+1 if k2 >= 0 else k; continue
                if name == "par":
                    j = k; continue
                k2 = seg.find("{", k)
                j = skip_balanced(seg, k) if k2 == k else k
                continue
            j += 1
        elif c in "{}" or c.isspace():
            j += 1
        else:
            rc = ap.rough_char(c)
            if rc: rough.append(rc)
            j += 1
    return "".join(rough), offs

def xetex_chapter_data(bk, ch):
    fn = os.path.join(XETEX_DIR, BOOKS[bk] + "_src.tex")
    if not os.path.exists(fn): return None
    content = open(fn, encoding="utf-8").read()
    if ch == 1:
        m = re.search(r"\\OneChap|\\(?:ChapOne|Chap)\{1\}", content)
    else:
        m = re.search(r"\\(?:Chap|ChapOne)\{" + str(ch) + r"\}", content)
    if not m: return None
    i = m.end()
    nm2 = re.search(r"\\OneChap|\\(?:Chap|ChapOne)\{\d+\}", content[i:])
    seg = content[i: i+nm2.start() if nm2 else len(content)]
    return parse_seg(seg)

OUT = "/home/gustav/f35/F35_MES_pipeline/source/4 - adding paragraphs/f35_with_paragraphs.txt"
out_ch = {}
for line in open(OUT, encoding="utf-8"):
    m = re.match(r"^(\d{2})(\d{3})(\d{3})\s+(.*)", line)
    if not m: continue
    out_ch.setdefault((int(m.group(1)), int(m.group(2))), []).append(m.group(4))
def out_data(bk, ch):
    rough, offs, pos = [], [], 0
    for text in out_ch[(bk, ch)]:
        text = re.sub(r"⋄\d+", "", text)
        for c in text:
            if c == "¶": offs.append(pos)
            else:
                rc = ap.rough_char(c)
                if rc: pos += 1
                rough.append(rc) if rc else None
    return "".join(rough), offs

report = []
mismatch = 0
n_usfx = n_xetex = 0
for bk in sorted(BOOKS):
    for ch in range(1, 1000):
        u = USFM_BOOK_FILES.get(bk)
        if not u: break
        verses = ap.parse_usfm_chapter(u, ch)
        if verses is None: break
        usfm_r, usfm_o = ap.usfm_para_offsets(verses)
        usfx = usfx_chapter_data(BOOKS[bk], ch)
        xet = xetex_chapter_data(bk, ch)
        outr, outo = out_data(bk, ch)
        issues = []
        for name, src in (("USFX", usfx), ("XETEX", xet)):
            if src is None: issues.append(name+":ABSENT"); continue
            r, o = src
            if name == "USFX": n_usfx += len(o)
            else: n_xetex += len(o)
            if r != usfm_r: issues.append("%s:TEXTE(%d vs %d)" % (name, len(r), len(usfm_r)))
            elif o != usfm_o: issues.append(name+":PARAG")
        if outr != usfm_r or outo != usfm_o: issues.append("OUT:DIFF")
        if issues:
            mismatch += 1
            report.append("%s %s: %s" % (BOOKS[bk], ch, "; ".join(issues)))
open("/tmp/opencode/compare_report.txt","w").write("\n".join(report))
print("chapitres en désaccord:", mismatch)
print("¶ : USFM 1879 | USFX %d | XETEX %d" % (n_usfx, n_xetex))
for ln in report: print(ln)
