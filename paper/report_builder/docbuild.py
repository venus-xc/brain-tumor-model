"""Small helper layer over python-docx for the OUTR report format (A4, Times New Roman)."""
import re, subprocess, tempfile, os, copy
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml
from lxml import etree

FONT = "Times New Roman"
ACCENT = RGBColor(0x1F, 0x3A, 0x68)


class Report:
    def __init__(self):
        self.d = Document()
        s = self.d.sections[0]
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.top_margin, s.bottom_margin, s.left_margin, s.right_margin = Cm(2.5), Cm(2.3), Cm(3.0), Cm(2.0)
        s.header_distance, s.footer_distance = Cm(1.0), Cm(1.0)
        st = self.d.styles["Normal"]; st.font.name = FONT; st.font.size = Pt(12)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        st.paragraph_format.space_after = Pt(6); st.paragraph_format.line_spacing = 1.4
        for lvl, size in [(1, 16), (2, 13), (3, 12)]:
            h = self.d.styles[f"Heading {lvl}"]; h.font.name = FONT; h.font.size = Pt(size); h.font.bold = True
            h.font.color.rgb = RGBColor(0, 0, 0); h.font.italic = False
            rf = h.element.rPr.rFonts; rf.set(qn("w:ascii"), FONT); rf.set(qn("w:hAnsi"), FONT); rf.set(qn("w:eastAsia"), FONT); rf.set(qn("w:cs"), FONT)
            pf = h.paragraph_format; pf.keep_with_next = True; pf.line_spacing = 1.15
            pf.space_before = Pt(18 if lvl == 1 else 12); pf.space_after = Pt(12 if lvl == 1 else 6)
        self._footer_page_number()
        self.fig_n = 0; self.tab_n = 0; self.eq_n = {}; self.figures = []; self.tables = []; self.chapter = 0
        self.first = True

    # ---------- basics ----------
    def _footer_page_number(self):
        p = self.d.sections[0].footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(); r.font.name = FONT; r.font.size = Pt(11)
        for t, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
            if t:
                e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); r._r.append(e)
            else:
                e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; r._r.append(e)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def runs(self, p, text, size=None, bold=False, italic=False, color=None):
        """**bold**, *italic* and ^sup^ / ~sub~ inline markup."""
        for tok in re.split(r"(\*\*.+?\*\*|\*[^*]+?\*|\^[^^]+?\^|~[^~]+?~)", text):
            if not tok: continue
            b, i, sup, sub = bold, italic, False, False
            if tok.startswith("**"): tok, b = tok[2:-2], True
            elif tok.startswith("*"): tok, i = tok[1:-1], True
            elif tok.startswith("^"): tok, sup = tok[1:-1], True
            elif tok.startswith("~"): tok, sub = tok[1:-1], True
            r = p.add_run(tok); r.font.name = FONT
            if b: r.bold = True
            if i: r.italic = True
            if sup: r.font.superscript = True
            if sub: r.font.subscript = True
            if size: r.font.size = Pt(size)
            if color: r.font.color.rgb = color
        return p

    def para(self, text, align="justify", size=None, bold=False, italic=False, before=0, after=6, indent=False, spacing=None, keep=False):
        p = self.d.add_paragraph()
        p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT, "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        pf = p.paragraph_format; pf.space_before = Pt(before); pf.space_after = Pt(after)
        if spacing: pf.line_spacing = spacing
        if indent: pf.first_line_indent = Cm(0.8)
        if keep: pf.keep_with_next = True
        return self.runs(p, text, size, bold, italic)

    def bullets(self, items, numbered=False):
        for k, it in enumerate(items, 1):
            p = self.d.add_paragraph(); pf = p.paragraph_format
            pf.left_indent = Cm(1.0); pf.first_line_indent = Cm(-0.6); pf.space_after = Pt(3); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            self.runs(p, (f"{k}.\t" if numbered else "•\t") + it)
            pf.tab_stops.add_tab_stop(Cm(1.0))

    # ---------- headings ----------
    def chapter_heading(self, title):
        self.chapter += 1; self.sec = 0
        h = self.d.add_heading(level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if not self.first: h.paragraph_format.page_break_before = True
        self.first = False
        self.runs(h, f"CHAPTER {self.chapter} – {title.upper()}")
        return h

    def front_heading(self, title, new_page=True):
        h = self.d.add_heading(level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER; self.runs(h, title)
        if new_page and not self.first: h.paragraph_format.page_break_before = True
        self.first = False
        return h

    def section(self, title):
        self.sec += 1; self.sub = 0
        h = self.d.add_heading(level=2); self.runs(h, f"{self.chapter}.{self.sec}  {title}")

    def subsection(self, title):
        self.sub += 1
        h = self.d.add_heading(level=3); self.runs(h, f"{self.chapter}.{self.sec}.{self.sub}  {title}")

    # ---------- figures / tables ----------
    def figure(self, path, caption, width_cm=15.5):
        self.fig_n += 1
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(2); p.paragraph_format.line_spacing = 1.0
        p.add_run().add_picture(path, width=Cm(width_cm))
        c = self.d.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.space_after = Pt(10); c.paragraph_format.line_spacing = 1.1
        self.runs(c, f"**Figure {self.fig_n}.** {caption}", size=10.5)
        self.figures.append(f"Figure {self.fig_n}. {caption}")
        return self.fig_n

    def table(self, caption, header, rows, widths_cm, font=10, align=None, highlight_tbd=True):
        self.tab_n += 1
        c = self.d.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.keep_with_next = True
        c.paragraph_format.space_before = Pt(8); c.paragraph_format.space_after = Pt(4); c.paragraph_format.line_spacing = 1.1
        self.runs(c, f"**Table {self.tab_n}.** {caption}", size=10.5)
        self.tables.append(f"Table {self.tab_n}. {caption}")
        t = self.d.add_table(rows=1 + len(rows), cols=len(header)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = self.d.styles["Table Grid"]; t.autofit = False
        grid = t._tbl.tblGrid
        for ci, (gc, w) in enumerate(zip(grid.findall(qn("w:gridCol")), widths_cm)):
            gc.set(qn("w:w"), str(int(w * 567)))
        for ci, w in enumerate(widths_cm):
            for row in t.rows: row.cells[ci].width = Cm(w)
        tblPr = t._tbl.tblPr; lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        for ri, row in enumerate([header] + rows):
            for ci, val in enumerate(row):
                cell = t.cell(ri, ci); cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1); p.paragraph_format.line_spacing = 1.05
                a = (align[ci] if align else ("left" if ci == 0 else "center"))
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if a == "center" else WD_ALIGN_PARAGRAPH.LEFT
                self.runs(p, str(val), size=font, bold=(ri == 0))
                if ri == 0: self._shade(cell, "DCE6F2")
                if highlight_tbd and "[TBD]" in str(val): self._shade(cell, "FFF2CC")
                # keep rows on one page
            trPr = t.rows[ri]._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        # repeat header row
        hdr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); hdr.append(th)
        sp = self.d.add_paragraph(); sp.paragraph_format.space_after = Pt(4)
        return t

    def _shade(self, cell, fill):
        tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill); tcPr.append(shd)

    # ---------- equations (LaTeX -> OMML through pandoc) ----------
    _cache = {}
    def _omml(self, latex):
        latex = re.sub(r"\\mathrm\{([^{}]*)\}", r"\\text{\1}", latex)
        if latex in self._cache: return self._cache[latex]
        with tempfile.TemporaryDirectory() as tmp:
            open(f"{tmp}/e.md", "w").write(f"$${latex}$$\n")
            subprocess.run(["pandoc", f"{tmp}/e.md", "-o", f"{tmp}/e.docx"], check=True)
            import zipfile
            x = zipfile.ZipFile(f"{tmp}/e.docx").read("word/document.xml").decode()
        m = re.search(r"<m:oMath>.*</m:oMath>", x, re.S).group(0)
        xml = m.replace("<m:oMath>", '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">', 1)
        self._cache[latex] = xml
        return xml

    def equation(self, latex):
        key = self.chapter; self.eq_n[key] = self.eq_n.get(key, 0) + 1
        p = self.d.add_paragraph(); pf = p.paragraph_format; pf.space_before = Pt(4); pf.space_after = Pt(8); pf.line_spacing = 1.0
        sec = self.d.sections[0]; usable = sec.page_width - sec.left_margin - sec.right_margin
        pf.tab_stops.add_tab_stop(int(usable / 2), WD_TAB_ALIGNMENT.CENTER); pf.tab_stops.add_tab_stop(usable, WD_TAB_ALIGNMENT.RIGHT)
        p.add_run("\t")
        om = parse_xml(self._omml(latex))
        # enlarge math font slightly
        for r in om.iter(qn("m:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr"); r.insert(1 if r.find(qn("m:rPr")) is not None else 0, rpr)
            f = OxmlElement("w:rFonts"); f.set(qn("w:ascii"), "Cambria Math"); f.set(qn("w:hAnsi"), "Cambria Math"); rpr.append(f)
        p._p.append(om)
        r = p.add_run(f"\t({self.chapter}.{self.eq_n[key]})"); r.font.size = Pt(11)
        return f"({self.chapter}.{self.eq_n[key]})"

    def toc_line(self, text, page, bold=False, indent=0.0, size=12):
        p = self.d.add_paragraph(); pf = p.paragraph_format; pf.space_after = Pt(3); pf.line_spacing = 1.15
        pf.left_indent = Cm(indent)
        sec = self.d.sections[0]; usable = sec.page_width - sec.left_margin - sec.right_margin
        pf.tab_stops.add_tab_stop(usable, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        self.runs(p, f"{text}\t{page}", size=size, bold=bold)

    def save(self, path):
        self.d.save(path)
