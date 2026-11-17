// IEEE-style B.Tech project presentation, light theme following the reference design.
// usage: node build_ppt.js <root with results/ and figs/> <out.pptx>
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const SK = "/root/.claude/skills/synced/eb966360-d534-422b-98e0-f21ab351bd74_78012257-1145-41eb-a04b-506a78af0285/pptx";
let applyTheme = async () => {};
try { applyTheme = require(SK + "/scripts/apply_theme.js").applyTheme; } catch (e) { console.log("apply_theme helper not found; skipping theme colours"); }

const ROOT = process.argv[2] || "..";
const OUTF = process.argv[3] || "deck.pptx";
const FIG = (n) => path.join(ROOT, "figs", n);
const M = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "metrics.json")));
const SEGF = path.join(ROOT, "results", "segmentation.json");
const SEG = fs.existsSync(SEGF) ? JSON.parse(fs.readFileSync(SEGF)) : null;
const PY = fs.existsSync(".venv/bin/python") ? ".venv/bin/python" : "python3";
const SIZES = JSON.parse(execSync(`${PY} -c "import json,glob;from PIL import Image;print(json.dumps({f:Image.open(f).size for f in glob.glob('${ROOT}/figs/*.png')+glob.glob('${ROOT}/figs/eq/*.png')+glob.glob('${ROOT}/figs/*.jpg')}))"`).toString());
const C = M.classical, D = M.deep, S = M.split, L = M.leakage;
const E = D.effb0_clean, CN = D.cnn_clean, SN = D.secnn_clean, EO = D.effb0_official;
const pc = (v, d = 1) => (100 * v).toFixed(d) + "%";

const THEME = {
  name: "OUTR Light", headFontFace: "Arial", bodyFontFace: "Calibri",
  colors: { dk1: "1F2937", lt1: "FFFFFF", dk2: "4B5563", lt2: "FBF1E1", accent1: "5B7FC8", accent2: "EE8F8B", accent3: "F2C64B",
            accent4: "8DBA7A", accent5: "F29A4A", accent6: "9B8BD4", hlink: "5B7FC8", folHlink: "6B7280" },
};
const H = { ink: "1F2937", grey: "4B5563", mute: "6B7280", cream: "FBF1E1", white: "FFFFFF", blue: "5B7FC8", pink: "EE8F8B", yel: "F2C64B",
            grn: "8DBA7A", org: "F29A4A", lblue: "E3EAF8", lpink: "FCE5E3", lyel: "FDF3D3", lgrn: "E6F1E0", lorg: "FDE9D7", line: "E8DCC8" };
const ACC = [H.blue, H.pink, H.yel, H.grn, H.org];
const LACC = { [H.blue]: H.lblue, [H.pink]: H.lpink, [H.yel]: H.lyel, [H.grn]: H.lgrn, [H.org]: H.lorg };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Brain Tumor Detection and Monitoring Using AI and ML";
pres.author = "Chinmayee Patra, Shruti Sameekshya Dehury";
const SC = pres.SchemeColor;

// ---------- layouts ----------
function corners(objs) {
  // blue L-shaped corner brackets (top-left, bottom-right) from the reference design
  objs.push({ rect: { x: 0, y: 0, w: 1.1, h: 0.16, fill: { color: H.blue } } });
  objs.push({ rect: { x: 0, y: 0, w: 0.16, h: 1.1, fill: { color: H.blue } } });
  objs.push({ rect: { x: 13.333 - 1.1, y: 7.5 - 0.16, w: 1.1, h: 0.16, fill: { color: H.blue } } });
  objs.push({ rect: { x: 13.333 - 0.16, y: 7.5 - 1.1, w: 0.16, h: 1.1, fill: { color: H.blue } } });
  return objs;
}
pres.defineSlideMaster({
  title: "CONTENT", background: { color: H.cream },
  objects: corners([
    { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.38, w: 9, h: 0.32, fontSize: 12, bold: true, color: H.pink, fontFace: "Arial", charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.7, w: 12.1, h: 0.75, fontSize: 32, bold: true, color: H.ink, fontFace: "Arial", margin: 0, valign: "middle", align: "left" }, text: "" } },
  ]),
  slideNumber: { x: 12.35, y: 6.88, w: 0.6, h: 0.3, fontSize: 11, color: H.grey, fontFace: "Arial", bold: true, align: "right" },
});
pres.defineSlideMaster({ title: "COVER", background: { color: H.cream }, objects: corners([]),
  slideNumber: { x: 12.35, y: 6.88, w: 0.6, h: 0.3, fontSize: 11, color: H.grey, fontFace: "Arial", bold: true, align: "right" } });

// ---------- helpers ----------
let slideNo = 0;
function content(kicker, title, sub) {
  const s = pres.addSlide({ masterName: "CONTENT" }); slideNo++;
  s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  if (sub) s.addText(sub, { x: 0.6, y: 1.45, w: 12.1, h: 0.4, fontSize: 15, color: H.grey, margin: 0, isTextBox: true, objectName: "subtitle" });
  return s;
}
function card(s, x, y, w, h, fill = H.white, name = "card") {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: H.line, width: 0.75 },
    shadow: { type: "outer", color: "C9B99E", opacity: 0.25, blur: 6, offset: 2, angle: 90 }, objectName: name });
}
function dot(s, x, y, d, color, label, fs = 14) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 }, objectName: "dot" });
  if (label !== undefined) s.addText(String(label), { x, y, w: d, h: d, align: "center", valign: "middle", fontSize: fs, bold: true, color: H.white, margin: 0, isTextBox: true, fontFace: "Arial" });
}
function img(s, file, x, y, w, h, opts = {}) {
  // fit inside box keeping aspect ratio
  const key = Object.keys(SIZES).find((k) => k.endsWith("/" + file) || k === FIG(file));
  const [iw, ih] = SIZES[key];
  let ww = w, hh = (w * ih) / iw;
  if (hh > h) { hh = h; ww = (h * iw) / ih; }
  const ox = opts.align === "left" ? x : x + (w - ww) / 2, oy = opts.valign === "top" ? y : y + (h - hh) / 2;
  s.addImage({ path: key, x: ox, y: oy, w: ww, h: hh, altText: opts.alt || file, objectName: "img" });
  return { x: ox, y: oy, w: ww, h: hh };
}
function eq(s, name, x, y, w, h, align = "left") {
  const key = Object.keys(SIZES).find((k) => k.endsWith("/eq/" + name + ".png"));
  const [iw, ih] = SIZES[key];
  let k = 1 / 300; // one consistent scale for every equation (about 19 pt)
  if (iw * k > w) k = w / iw;
  if (ih * k > h) k = h / ih;
  const ww = iw * k, hh = ih * k, ox = align === "center" ? x + (w - ww) / 2 : x, oy = y + (h - hh) / 2;
  s.addImage({ path: key, x: ox, y: oy, w: ww, h: hh, altText: "equation " + name, objectName: "equation" });
}
function label(s, text, x, y, w, color = H.blue, fs = 13) {
  s.addText(text.toUpperCase(), { x, y, w, h: 0.32, fontSize: fs, bold: true, color, charSpacing: 1.5, margin: 0, isTextBox: true, fontFace: "Arial" });
}
function body(s, text, x, y, w, h, fs = 15, opts = {}) {
  s.addText(text, Object.assign({ x, y, w, h, fontSize: fs, color: H.ink, margin: 0, valign: "top", isTextBox: true, paraSpaceAfter: 4 }, opts));
}
function bullets(s, items, x, y, w, h, fs = 15, color = H.blue) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1 } })),
    { x, y, w, h, fontSize: fs, color: H.ink, valign: "top", margin: 0, paraSpaceAfter: 10, isTextBox: true });
}
function kpi(s, x, y, w, h, value, cap, color) {
  card(s, x, y, w, h);
  dot(s, x + 0.25, y + (h - 0.62) / 2, 0.62, color);
  s.addText(value, { x: x + 1.0, y: y + 0.12, w: w - 1.1, h: 0.5, fontSize: 24, bold: true, color: H.ink, margin: 0, valign: "middle", fontFace: "Arial", isTextBox: true });
  s.addText(cap, { x: x + 1.0, y: y + 0.64, w: w - 1.1, h: h - 0.7, fontSize: 13, color: H.grey, margin: 0, valign: "top", isTextBox: true });
}
function flow(s, steps, x, y, w, h, gap = 0.28) {
  const n = steps.length, bw = (w - gap * (n - 1)) / n;
  steps.forEach(([t, sub], i) => {
    const bx = x + i * (bw + gap), col = ACC[i % ACC.length];
    card(s, bx, y, bw, h, LACC[col]);
    dot(s, bx + bw / 2 - 0.3, y - 0.3, 0.6, col, String(i + 1).padStart(2, "0"), 13);
    s.addText(t, { x: bx + 0.08, y: y + 0.42, w: bw - 0.16, h: 0.4, align: "center", fontSize: 14, bold: true, color: H.ink, margin: 0, fontFace: "Arial", isTextBox: true });
    s.addText(sub, { x: bx + 0.1, y: y + 0.85, w: bw - 0.2, h: h - 0.95, align: "center", fontSize: 12, color: H.grey, margin: 0, valign: "top", isTextBox: true });
    if (i < n - 1) s.addShape(pres.shapes.LINE, { x: bx + bw + 0.03, y: y + h / 2, w: gap - 0.06, h: 0, line: { color: H.mute, width: 1.25, endArrowType: "triangle" } });
  });
}
function note(s, text, y = 6.55, color = H.blue) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 11.6, h: 0.5, rectRadius: 0.1, fill: { color: LACC[color] }, line: { color, width: 1 }, objectName: "note" });
  s.addText(text, { x: 0.8, y, w: 11.2, h: 0.5, fontSize: 13.5, bold: true, color: H.ink, valign: "middle", margin: 0, isTextBox: true });
}
function table(s, rows, x, y, w, colW, fs = 13, boldLast = false) {
  const data = rows.map((r, ri) => r.map((c, ci) => ({ text: String(c), options: {
    bold: ri === 0 || (boldLast && ri === rows.length - 1), color: ri === 0 ? H.white : H.ink, fontSize: fs,
    fill: { color: ri === 0 ? H.blue : (boldLast && ri === rows.length - 1 ? H.lyel : (ri % 2 ? H.white : "F8F4EC")) },
    align: ci === 0 ? "left" : "center", valign: "middle", margin: [3, 6, 3, 6] } })));
  s.addTable(data, { x, y, w, colW, border: { type: "solid", color: H.line, pt: 0.75 }, rowH: 0.42, fontFace: "Calibri" });
}

// ======================= 1. TITLE =======================
{
  const s = pres.addSlide({ masterName: "COVER" }); slideNo++;
  s.addText("B.TECH PROJECT PRESENTATION  |  CSE (AI & ML)", { x: 0.75, y: 0.6, w: 8, h: 0.35, fontSize: 13, bold: true, color: H.pink, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText([{ text: "Brain Tumor Detection", options: { breakLine: true } }, { text: "and Monitoring", options: { color: H.blue } }],
    { x: 0.75, y: 1.05, w: 8.2, h: 1.7, fontSize: 44, bold: true, color: H.ink, margin: 0, fontFace: "Arial", isTextBox: true, valign: "top" });
  s.addText("Using Artificial Intelligence and Machine Learning on public MRI data", { x: 0.75, y: 2.85, w: 8, h: 0.45, fontSize: 18, color: H.grey, margin: 0, isTextBox: true });
  card(s, 0.75, 3.6, 6.6, 1.55, H.white);
  s.addText("PRESENTED BY", { x: 1.0, y: 3.75, w: 4, h: 0.3, fontSize: 12, bold: true, color: H.blue, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText([{ text: "Chinmayee Patra  |  23110206", options: { breakLine: true } }, { text: "Shruti Sameekshya Dehury  |  23110234" }],
    { x: 1.0, y: 4.1, w: 6.2, h: 0.9, fontSize: 17, bold: true, color: H.ink, margin: 0, isTextBox: true, paraSpaceAfter: 4 });
  s.addText([{ text: "Under the guidance of ", options: {} }, { text: "Mrs. Swarna Lata Pati", options: { bold: true } }, { text: ", Assistant Professor", options: {} }],
    { x: 0.75, y: 5.45, w: 8, h: 0.35, fontSize: 15, color: H.ink, margin: 0, isTextBox: true });
  s.addText("School of Computer Science  •  Odisha University of Technology and Research, Bhubaneswar", { x: 0.75, y: 5.85, w: 9, h: 0.35, fontSize: 13, color: H.grey, margin: 0, isTextBox: true });
  s.addText("November 2026", { x: 0.75, y: 6.25, w: 4, h: 0.3, fontSize: 13, bold: true, color: H.blue, margin: 0, isTextBox: true });
  // logo + playful circles (reference motif)
  dot(s, 8.85, 1.1, 1.1, H.yel); dot(s, 11.5, 0.75, 0.75, H.pink); dot(s, 12.0, 5.2, 0.9, H.grn); dot(s, 9.0, 5.6, 0.6, H.org);
  s.addShape(pres.shapes.OVAL, { x: 9.15, y: 1.65, w: 3.6, h: 3.6, fill: { color: H.white }, line: { color: H.blue, width: 3 }, objectName: "logo-ring" });
  img(s, "outr_logo_round.png", 9.35, 1.85, 3.2, 3.2, { alt: "OUTR logo" });
}

// ======================= 2. OVERVIEW =======================
{
  const s = content("01 | Project overview", "What we built", "A reproducible pipeline that classifies, explains and measures brain tumours in MRI slices.");
  kpi(s, 0.6, 2.05, 2.85, 1.15, "3,264", "public MRI images", H.blue);
  kpi(s, 3.68, 2.05, 2.85, 1.15, "4", "classes incl. no tumour", H.pink);
  kpi(s, 6.76, 2.05, 2.85, 1.15, "7", "ML / CNN models compared", H.yel);
  kpi(s, 9.84, 2.05, 2.85, 1.15, pc(E.accuracy), "best test accuracy", H.grn);
  card(s, 0.6, 3.55, 5.9, 2.75, H.lblue);
  label(s, "The question we explore", 0.9, 3.75, 5.3);
  body(s, "Can machine learning reliably recognise the tumour type in a single MRI slice, show where it looked, and measure how the tumour changes over time?", 0.9, 4.2, 5.3, 1.9, 19, { bold: true });
  card(s, 6.8, 3.55, 5.9, 2.75, H.white);
  label(s, "What the system connects", 7.1, 3.75, 5.3, H.pink);
  bullets(s, ["Public dataset audit and leakage-free split", "Classical ML, custom CNN, SE-CNN and EfficientNet-B0",
              "Grad-CAM / Grad-CAM++ explanation of every prediction", "U-Net segmentation, measurements and follow-up check", "FastAPI web app with PDF report"], 7.1, 4.2, 5.4, 2.0, 15);
}

// ======================= 3. PROBLEM =======================
{
  const s = content("01 | Problem context", "Why automate brain MRI reading?", "MRI is the standard test, but reading many slices by eye is slow and depends on experience.");
  card(s, 0.6, 2.05, 5.6, 3.95, H.white);
  label(s, "A practical scenario", 0.9, 2.25, 5);
  body(s, "A patient with headaches is scanned. The radiologist must check dozens of slices, decide whether a lesion is present, and name its likely type.", 0.9, 2.7, 5.0, 1.45, 16);
  body(s, "Later scans must be compared with the first one to decide whether treatment is working.", 0.9, 4.15, 5.0, 0.8, 16);
  body(s, "Our system is a second reader: it flags, explains and measures. It does not diagnose.", 0.9, 5.0, 5.0, 0.8, 16, { bold: true, color: H.blue });
  card(s, 6.5, 2.05, 6.2, 3.95, H.lblue);
  label(s, "Where AI helps", 6.8, 2.25, 5.6, H.pink);
  const st = [["SCAN", "MRI slice", H.blue], ["AI SECOND READER", "class + heatmap + size", H.pink], ["DOCTOR REVIEW", "final decision", H.grn]];
  st.forEach(([t, sub, c], i) => {
    const yy = 2.8 + i * 1.03;
    card(s, 6.85, yy, 5.5, 0.82, H.white);
    dot(s, 7.0, yy + 0.13, 0.56, c, i + 1, 14);
    s.addText(t, { x: 7.75, y: yy + 0.08, w: 4.4, h: 0.38, fontSize: 15, bold: true, color: H.ink, margin: 0, isTextBox: true, fontFace: "Arial" });
    s.addText(sub, { x: 7.75, y: yy + 0.44, w: 4.4, h: 0.3, fontSize: 13, color: H.grey, margin: 0, isTextBox: true });
  });
  note(s, "Goal: faster, more consistent triage with visual evidence, not replacement of the radiologist.", 6.3, H.yel);
}

// ======================= 4. TUMOUR CLASSES =======================
{
  const s = content("01 | Clinical context", "Four classes our models must tell apart", "Real examples from the held-out test set after preprocessing.");
  const cls = [["No tumour", "Normal slice; no focal lesion", "ppt_no_tumor.png", H.grn], ["Glioma", "Arises from glial cells, intra-axial, irregular borders", "ppt_glioma.png", H.pink],
               ["Meningioma", "From the meninges, extra-axial, well circumscribed", "ppt_meningioma.png", H.blue], ["Pituitary tumour", "In the sella turcica at the skull base", "ppt_pituitary.png", H.yel]];
  cls.forEach(([t, d, f, c], i) => {
    const x = 0.6 + i * 3.08;
    card(s, x, 2.05, 2.85, 4.55, H.white);
    img(s, f, x + 0.22, 2.25, 2.41, 2.41, { alt: t });
    dot(s, x + 0.22, 4.85, 0.36, c);
    s.addText(t, { x: x + 0.68, y: 4.82, w: 2.1, h: 0.42, fontSize: 17, bold: true, color: H.ink, margin: 0, isTextBox: true, fontFace: "Arial" });
    body(s, d, x + 0.22, 5.35, 2.45, 1.1, 14, { color: H.grey });
  });
}

// ======================= 5. OBJECTIVES =======================
{
  const s = content("01 | Project definition", "Objectives and scope");
  card(s, 0.6, 1.75, 6.0, 4.75, H.white);
  label(s, "What we set out to do", 0.9, 1.95, 5.4, H.blue);
  bullets(s, ["Use a public MRI dataset and audit it for duplicate images", "Build a leakage-free 70 / 15 / 15 split", "Compare HOG + classical ML with CNN and transfer learning",
              "Test channel attention (SE blocks) with an ablation", "Explain predictions with Grad-CAM and Grad-CAM++", "Segment tumours, measure size, compare follow-ups", "Deploy in a web app with PDF reports"], 0.9, 2.45, 5.5, 3.9, 18);
  card(s, 6.85, 1.75, 5.85, 4.75, H.lpink);
  label(s, "Outside the current scope", 7.15, 1.95, 5.3, H.pink);
  bullets(s, ["Full 3D volumes or multi-sequence MRI", "Glioma grading or molecular sub-types", "Clinical validation or regulatory approval", "Automatic registration of follow-up scans",
              "Use as a diagnostic device"], 7.15, 2.45, 5.3, 3.9, 19);
}

// ======================= 6. LITERATURE =======================
{
  const s = content("02 | Literature review", "What earlier work reports", "Most studies use the 3-class Figshare set with image-level splits, so numbers are not directly comparable.");
  table(s, [["Study (IEEE ref.)", "Method", "Dataset", "Reported"],
            ["Cheng et al., 2015 [1]", "Region augmentation + BoW + SVM", "Figshare, 3 classes", "91.28%"],
            ["Afshar et al., 2018 [2]", "Capsule network", "Figshare, 3 classes", "90.89%"],
            ["Swati et al., 2019 [3]", "VGG-19 fine-tuning", "Figshare, 3 classes", "94.82%"],
            ["Deepak & Ameer, 2019 [4]", "GoogLeNet transfer learning", "Figshare, 3 classes", "97.1%"],
            ["Badža & Barjaktarović, 2020 [5]", "Custom CNN, 10-fold CV", "Figshare, 3 classes", "96.56%"],
            ["This work", "HOG+ML, CNN, SE-CNN, EfficientNet-B0", "4 classes, de-duplicated", pc(E.accuracy, 2)]],
        0.6, 2.05, 12.1, [3.4, 4.1, 2.9, 1.7], 16, true);
  note(s, "Research gap: duplicate images across train / test splits can inflate accuracy. We measure and remove this leakage.", 5.95, H.pink);
}

// ======================= 7. DATASET =======================
{
  const s = content("03 | Data", "The dataset: public and audited", "Brain Tumor Classification (MRI), Bhuvaji et al., Kaggle / GitHub mirror. Segmentation masks: Figshare (Cheng).");
  card(s, 0.6, 2.05, 7.3, 4.45, H.white);
  img(s, "fig_class_dist.png", 0.8, 2.2, 6.9, 4.15, { alt: "class distribution" });
  card(s, 8.15, 2.05, 4.55, 4.45, H.lblue);
  label(s, "Audit summary", 8.45, 2.25, 4.0);
  const rows = [[S.total_images.toLocaleString(), "images in the original release"], [String(S.images_in_duplicate_clusters), `images in ${S.duplicate_clusters} near-duplicate groups`],
                [String(S.conflicting_label_clusters), "groups with conflicting labels (removed)"], [S.unique_images_kept.toLocaleString(), "unique images kept"]];
  rows.forEach(([v, t], i) => {
    s.addText(v, { x: 8.45, y: 2.75 + i * 0.9, w: 1.55, h: 0.6, fontSize: 24, bold: true, color: ACC[i], margin: 0, valign: "middle", fontFace: "Arial", isTextBox: true });
    s.addText(t, { x: 10.05, y: 2.75 + i * 0.9, w: 2.5, h: 0.6, fontSize: 13.5, color: H.ink, margin: 0, valign: "middle", isTextBox: true });
  });
}

// ======================= 8. LEAKAGE =======================
{
  const s = content("03 | Data quality", "We found leakage in the official split", "Cosine similarity of 32×32 thumbnails ≥ 0.98 marks two images as near-duplicates.");
  card(s, 0.6, 2.05, 6.4, 3.0, H.white);
  img(s, "ppt_leak_pair.png", 0.75, 2.15, 6.1, 2.8, { alt: "duplicate pair" });
  card(s, 7.25, 2.05, 5.45, 3.0, H.white);
  img(s, "ppt_leak_bar.png", 7.4, 2.15, 5.15, 2.8, { alt: "share of duplicated test images" });
  const big = Math.round((100 * L.official_test_near_dup) / L.n_test);
  card(s, 0.6, 5.3, 3.6, 1.25, H.lpink);
  s.addText(big + "%", { x: 0.8, y: 5.38, w: 3.2, h: 0.65, fontSize: 32, bold: true, color: H.pink, margin: 0, fontFace: "Arial", isTextBox: true });
  s.addText("of official test images have a copy in training", { x: 0.8, y: 5.98, w: 3.3, h: 0.5, fontSize: 13, color: H.ink, margin: 0, isTextBox: true });
  card(s, 4.45, 5.3, 8.25, 1.25, H.lgrn);
  label(s, "Our fix", 4.75, 5.42, 3, H.grn);
  body(s, `Group duplicates, keep one per group, then a stratified 70 / 15 / 15 split: ${S.split_sizes.train} train, ${S.split_sizes.val} validation, ${S.split_sizes.test} test images.`, 4.75, 5.8, 7.8, 0.7, 15);
}

// ======================= 9. PREPROCESSING =======================
{
  const s = content("03 | Data preparation", "From raw slice to model-ready tensor", "The same steps run at training and at inference time.");
  flow(s, [["LOAD", "JPEG / PNG / DICOM to grayscale"], ["CROP", "largest brain contour bounding box"], ["CLAHE", "clip 2.0, tile grid 8×8"], ["RESIZE", "128 px (CNN, HOG), 160 px (EfficientNet)"],
           ["NORMALISE", "ImageNet mean/std or (x−0.5)/0.25"], ["AUGMENT", "flip, ±10° rotate, scale, brightness"]], 0.6, 2.35, 12.1, 1.65);
  card(s, 0.6, 4.35, 12.1, 2.25, H.white);
  img(s, "fig_preprocessing.png", 0.8, 4.45, 11.7, 2.05, { alt: "preprocessing steps" });
}

// ======================= 10. ARCHITECTURE =======================
{
  const s = content("04 | System design", "Implemented system architecture");
  card(s, 0.6, 1.7, 12.1, 4.75, H.white);
  img(s, "fig_architecture.png", 0.8, 1.8, 11.7, 4.55, { alt: "system architecture" });
  note(s, "Every model is trained and tested on the same leakage-free split, so the comparison is fair.", 6.6, H.blue);
}

// ======================= 11. CLASSICAL ML =======================
{
  const s = content("05 | Machine learning", "Baselines: HOG features + classical ML", `Each slice becomes a ${C.hog_dim}-value gradient histogram, reduced to 150 values by PCA.`);
  card(s, 0.6, 2.05, 5.0, 4.5, H.white);
  img(s, "fig_hog.png", 0.75, 2.2, 4.7, 2.4, { alt: "HOG visualisation" });
  eq(s, "hog", 0.9, 4.8, 4.4, 0.55, "center");
  body(s, "9 orientation bins, 16×16-pixel cells, 2×2-cell blocks", 0.9, 5.55, 4.4, 0.8, 13.5, { color: H.grey, align: "center" });
  card(s, 5.85, 2.05, 6.85, 4.5, H.lblue);
  label(s, "Support Vector Machine (RBF kernel)", 6.15, 2.25, 6.3);
  eq(s, "svm", 6.15, 2.7, 4.6, 0.75);
  eq(s, "rbf", 6.15, 3.55, 4.6, 0.45);
  label(s, "Also compared", 6.15, 4.3, 6.3, H.pink);
  const others = [["Random Forest", pc(C["Random Forest"].accuracy)], ["k-NN (k = 3)", pc(C["k-NN"].accuracy)], ["Logistic Regression", pc(C["Logistic Regression"].accuracy)], ["SVM (RBF), best", pc(C["SVM (RBF)"].accuracy)]];
  others.forEach(([t, v], i) => {
    const x = 6.15 + (i % 2) * 3.2, y = 4.75 + Math.floor(i / 2) * 0.82;
    card(s, x, y, 3.0, 0.68, H.white);
    s.addText([{ text: t + "  ", options: { color: H.ink } }, { text: v, options: { bold: true, color: H.ink } }], { x: x + 0.15, y, w: 2.8, h: 0.68, fontSize: 14, margin: 0, valign: "middle", isTextBox: true });
  });
}

// ======================= 12. CNN + SE =======================
{
  const s = content("05 | Deep learning", "Custom CNN and SE-CNN (trained from scratch)", `Plain CNN ${CN.params.toLocaleString()} parameters; SE-CNN ${SN.params.toLocaleString()} parameters.`);
  card(s, 0.6, 2.05, 12.1, 2.35, H.white);
  img(s, "fig_cnn.png", 0.8, 2.12, 11.7, 2.2, { alt: "CNN architecture" });
  card(s, 0.6, 4.6, 5.9, 1.95, H.lblue);
  label(s, "Convolution and softmax", 0.9, 4.75, 5.4);
  eq(s, "conv", 0.9, 5.15, 5.3, 0.5);
  eq(s, "softmax", 0.9, 5.7, 2.5, 0.75);
  card(s, 6.8, 4.6, 5.9, 1.95, H.lpink);
  label(s, "Squeeze-and-Excitation block", 7.1, 4.75, 5.4, H.pink);
  eq(s, "squeeze", 7.1, 5.12, 3.6, 0.65);
  eq(s, "excite", 7.1, 5.85, 5.4, 0.42);
}

// ======================= 13. TRANSFER LEARNING =======================
{
  const s = content("05 | Deep learning", "Transfer learning with EfficientNet-B0", `ImageNet-pretrained backbone, new 4-class head, fine-tuned end-to-end (${(E.params / 1e6).toFixed(1)} M parameters).`);
  card(s, 0.6, 2.05, 12.1, 2.2, H.white);
  img(s, "fig_effnet.png", 0.8, 2.12, 11.7, 2.05, { alt: "EfficientNet-B0" });
  card(s, 0.6, 4.45, 6.6, 2.1, H.lyel);
  label(s, "Loss: class-weighted cross-entropy", 0.9, 4.6, 6.0, H.org);
  eq(s, "ce", 0.9, 5.0, 4.0, 0.8);
  eq(s, "cw", 5.1, 5.05, 1.4, 0.65);
  body(s, "Label smoothing ε = 0.05; class weights offset the small no-tumour class", 0.9, 5.95, 6.0, 0.5, 13, { color: H.grey });
  card(s, 7.45, 4.45, 5.25, 2.1, H.white);
  label(s, "Training setup", 7.75, 4.6, 4.7);
  bullets(s, ["AdamW, one-cycle LR (max 1e-3)", `${E.epochs} epochs, batch 32, 160×160 input`, "Best epoch chosen on validation set", "Seed 42 for reproducibility"], 7.75, 5.0, 4.8, 1.5, 14);
}

// ======================= 14. SEGMENTATION =======================
{
  const s = content("05 | Segmentation", "U-Net and Attention U-Net for tumour outlines", "Trained on the Figshare tumour masks (3,064 slices, 233 patients) with a patient-level split.");
  card(s, 0.6, 2.05, 7.0, 4.5, H.white);
  img(s, "fig_unet.png", 0.75, 2.15, 6.7, 4.3, { alt: "Attention U-Net" });
  card(s, 7.85, 2.05, 4.85, 2.1, H.lpink);
  label(s, "Attention gate", 8.15, 2.2, 4.3, H.pink);
  eq(s, "ag", 8.15, 2.65, 4.35, 0.4);
  body(s, "Suppresses skull and healthy tissue on skip connections before decoding", 8.15, 3.2, 4.3, 0.85, 13.5, { color: H.grey });
  card(s, 7.85, 4.4, 4.85, 2.15, H.lgrn);
  label(s, "Loss and test results", 8.15, 4.55, 4.3, H.grn);
  eq(s, "segloss", 8.15, 4.92, 4.35, 0.5);
  if (SEG) {
    [["U-Net", SEG.unet_dice, SEG.unet_iou], ["Attention U-Net", SEG.attunet_dice, SEG.attunet_iou]].forEach(([n, d, i], k) => {
      s.addText([{ text: n + "   ", options: { bold: true } }, { text: `Dice ${d.toFixed(3)}  |  IoU ${i.toFixed(3)}`, options: {} }],
        { x: 8.15, y: 5.5 + k * 0.45, w: 4.4, h: 0.4, fontSize: 14, color: H.ink, margin: 0, valign: "middle", isTextBox: true });
    });
  } else { eq(s, "dice", 8.15, 5.6, 3.2, 0.6); }
}

// ======================= 15. EXPERIMENT SETUP =======================
{
  const s = content("06 | Experiments", "How we evaluated the models", "One fixed split, one test run per model, seed 42.");
  kpi(s, 0.6, 2.05, 2.85, 1.1, "70/15/15", "train / val / test", H.blue);
  kpi(s, 3.68, 2.05, 2.85, 1.1, String(S.split_sizes.train), "training images", H.pink);
  kpi(s, 6.76, 2.05, 2.85, 1.1, String(S.split_sizes.test), "unseen test images", H.yel);
  kpi(s, 9.84, 2.05, 2.85, 1.1, "42", "random seed", H.grn);
  card(s, 0.6, 3.45, 12.1, 3.1, H.white);
  label(s, "Metrics we tracked", 0.9, 3.6, 11.5);
  eq(s, "acc", 0.9, 4.05, 4.3, 0.75);
  eq(s, "prec", 5.5, 4.1, 6.9, 0.65);
  eq(s, "f1", 0.9, 5.05, 4.3, 0.75);
  body(s, "Macro averages give each class equal weight. ROC-AUC (one-vs-rest) measures ranking quality independent of the threshold.", 5.5, 5.05, 6.9, 1.0, 15, { color: H.grey });
}

// ======================= 16. RESULTS TABLE =======================
{
  const s = content("06 | Results", "Test-set results of all seven models", `Held-out test set, n = ${S.split_sizes.test}, leakage-free split.`);
  const rows = [["Model", "Accuracy", "Macro precision", "Macro recall", "Macro F1", "ROC-AUC"]];
  for (const k of ["Logistic Regression", "k-NN", "Random Forest", "SVM (RBF)"]) { const r = C[k]; rows.push(["HOG + " + k, pc(r.accuracy, 2), r.macro_precision.toFixed(3), r.macro_recall.toFixed(3), r.macro_f1.toFixed(3), r.roc_auc_ovr_macro.toFixed(3)]); }
  for (const [k, n] of [["cnn_clean", "Custom CNN (scratch)"], ["secnn_clean", "SE-CNN (scratch)"], ["effb0_clean", "EfficientNet-B0 (transfer)"]]) { const r = D[k]; rows.push([n, pc(r.accuracy, 2), r.macro_precision.toFixed(3), r.macro_recall.toFixed(3), r.macro_f1.toFixed(3), r.roc_auc_ovr_macro.toFixed(3)]); }
  table(s, rows, 0.6, 2.0, 12.1, [3.9, 1.6, 1.7, 1.6, 1.6, 1.7], 14, true);
  note(s, `Transfer learning wins: EfficientNet-B0 reaches ${pc(E.accuracy)} accuracy and ${E.roc_auc_ovr_macro.toFixed(3)} ROC-AUC; best classical model: HOG + SVM (${pc(C["SVM (RBF)"].accuracy)}).`, 6.0, H.grn);
}

// ======================= 17. RESULT PLOTS =======================
{
  const s = content("06 | Results", "Where the best model succeeds and fails");
  card(s, 0.6, 1.7, 7.9, 4.85, H.white);
  img(s, "fig_confusion.png", 0.75, 1.8, 7.6, 4.65, { alt: "confusion matrices" });
  card(s, 8.75, 1.7, 3.95, 4.85, H.white);
  img(s, "fig_roc.png", 8.85, 1.85, 3.75, 4.55, { alt: "ROC curves" });
  note(s, "Most remaining errors are between glioma and meningioma, which can look alike on a single contrast-enhanced slice.", 6.7, H.blue);
}

// ======================= 18. TRAINING CURVES =======================
{
  const s = content("06 | Results", "Learning behaviour of the deep models", "Dashed = training, solid = validation. Transfer learning converges fastest.");
  card(s, 0.6, 2.05, 12.1, 4.5, H.white);
  img(s, "fig_curves.png", 0.8, 2.15, 11.7, 4.3, { alt: "training curves" });
}
// ======================= 18b. MODEL RANKING =======================
{
  const s = content("06 | Results", "Model ranking on the same test set", "Each step from hand-crafted features to transfer learning improves accuracy.");
  card(s, 0.6, 2.05, 12.1, 4.5, H.white);
  img(s, "fig_comparison.png", 0.8, 2.15, 11.7, 4.3, { alt: "model comparison" });
}

// ======================= 19. XAI =======================
{
  const s = content("07 | Explainable AI", "Grad-CAM and Grad-CAM++: where did the model look?");
  card(s, 0.6, 1.7, 6.6, 5.0, H.white);
  img(s, "fig_gradcam.png", 0.75, 1.8, 6.3, 4.8, { alt: "Grad-CAM examples" });
  card(s, 7.45, 1.7, 5.25, 2.5, H.lblue);
  label(s, "Grad-CAM", 7.75, 1.85, 4.7);
  eq(s, "gc_w", 7.75, 2.25, 2.4, 0.85);
  eq(s, "gc_map", 7.75, 3.2, 4.3, 0.8);
  card(s, 7.45, 4.4, 5.25, 2.3, H.lpink);
  label(s, "Grad-CAM++ pixel weights", 7.75, 4.55, 4.7, H.pink);
  eq(s, "gcpp", 7.75, 4.95, 4.7, 0.75);
  body(s, "Clear cases peak over the lesion region; maps are coarse (5×5) and show focus, not borders.", 7.75, 5.85, 4.7, 0.75, 13.5, { color: H.grey });
}

// ======================= 20. DISCUSSION =======================
{
  const s = content("08 | Discussion", "What the results really mean");
  card(s, 0.6, 1.75, 6.0, 4.4, H.lgrn);
  label(s, "What went well", 0.9, 1.95, 5.4, H.grn);
  bullets(s, [`Transfer learning beat scratch CNNs (${pc(E.accuracy)} vs ${pc(Math.max(CN.accuracy, SN.accuracy))})`, `HOG + SVM is a strong classical baseline (${pc(C["SVM (RBF)"].accuracy)})`,
              `SE blocks changed scratch-CNN accuracy by ${(100 * (SN.accuracy - CN.accuracy)).toFixed(1)} points`, "Heatmaps point to the lesion region in clear cases", "Whole pipeline is scripted and reproducible"], 0.9, 2.5, 5.5, 3.6, 19);
  card(s, 6.85, 1.75, 5.85, 4.4, H.lpink);
  label(s, "What we must not overclaim", 7.15, 1.95, 5.3, H.pink);
  bullets(s, ["Single 2D slices, not 3D volumes", "No patient IDs in the classification dataset", "Not validated by radiologists or on other hospitals' data", "Follow-up module tested only on controlled mask pairs", "Not a medical device"], 7.15, 2.5, 5.3, 3.6, 19);
  if (EO) note(s, `Same EfficientNet-B0 on the official (leaky) split: ${pc(EO.accuracy)} vs ${pc(E.accuracy)} on our clean split. The split changes the reported number.`, 6.35, H.yel);
}

// ======================= 21. MEASUREMENT / FOLLOW-UP =======================
{
  const s = content("09 | Monitoring", "Tumour measurement and follow-up comparison", "From the segmentation mask: area, longest diameter d1 and perpendicular diameter d2.");
  card(s, 0.6, 2.05, 12.1, 2.7, H.white);
  img(s, "fig_rano.png", 0.8, 2.12, 11.7, 2.55, { alt: "follow-up decision flow" });
  card(s, 0.6, 4.95, 7.3, 1.6, H.lyel);
  label(s, "Measurements", 0.9, 5.08, 6.8, H.org);
  eq(s, "area", 0.9, 5.45, 3.0, 0.4);
  eq(s, "rano", 0.9, 5.9, 6.8, 0.6);
  card(s, 8.15, 4.95, 4.55, 1.6, H.lgrn);
  label(s, "Honest scope", 8.45, 5.08, 4.0, H.grn);
  body(s, "2D area and diameters only, no volume from one slice. Clinical RANO also uses steroid dose and neurological status.", 8.45, 5.45, 4.05, 1.05, 13.5);
}

// ======================= 22. IMPLEMENTATION =======================
{
  const s = content("10 | Implementation", "Web application and tools");
  card(s, 0.6, 1.7, 12.1, 3.2, H.white);
  img(s, "fig_inference.png", 0.8, 1.8, 11.7, 3.0, { alt: "inference output" });
  const tools = [["PYTORCH + TIMM", "CNN, SE-CNN, EfficientNet"], ["SCIKIT-LEARN", "HOG + SVM / RF / k-NN / LR"], ["OPENCV", "crop, CLAHE, overlays"], ["FASTAPI", "predict, follow-up, report"], ["REPORTLAB", "PDF report"], ["PYTEST + DOCKER", "tests, deployment"]];
  tools.forEach(([t, d], i) => {
    const x = 0.6 + (i % 3) * 4.08, y = 5.1 + Math.floor(i / 3) * 0.78;
    card(s, x, y, 3.85, 0.66, H.white);
    dot(s, x + 0.15, y + 0.15, 0.36, ACC[i % 5]);
    s.addText([{ text: t, options: { bold: true, color: H.ink, breakLine: true } }, { text: d, options: { color: H.grey, fontSize: 12 } }], { x: x + 0.65, y: y + 0.03, w: 3.1, h: 0.6, fontSize: 13, margin: 0, valign: "middle", isTextBox: true });
  });
}

// ======================= 23. LIMITS & FUTURE =======================
{
  const s = content("11 | Conclusion & future work", "Limitations and next steps");
  card(s, 0.6, 1.75, 6.0, 4.6, H.white);
  label(s, "Current limits", 0.9, 1.95, 5.4, H.pink);
  bullets(s, ["2D slices only; no 3D context", "No glioma grading", "Classification data lacks patient IDs", "Follow-up needs aligned, comparable slices", "Coarse 5×5 Grad-CAM resolution"], 0.9, 2.5, 5.5, 3.8, 20);
  card(s, 6.85, 1.75, 5.85, 4.6, H.lblue);
  label(s, "Next development", 7.15, 1.95, 5.3, H.blue);
  bullets(s, ["3D multi-sequence models on BraTS", "External test set from another hospital", "Uncertainty estimates and calibration", "Automatic registration of follow-up scans", "Reader study with radiologists"], 7.15, 2.5, 5.3, 3.8, 20);
}

// ======================= 24. CONCLUSION =======================
{
  const s = content("11 | Closing", "Conclusion");
  card(s, 0.6, 1.75, 7.6, 4.8, H.white);
  label(s, "What we delivered", 0.9, 1.95, 7.0, H.blue);
  body(s, `A reproducible pipeline on public MRI data: leakage audit, seven compared models with EfficientNet-B0 best at ${pc(E.accuracy)} accuracy and ${E.roc_auc_ovr_macro.toFixed(3)} ROC-AUC, Grad-CAM explanations, segmentation-based measurement and a web app with PDF reports.`, 0.9, 2.4, 7.0, 2.2, 18, { bold: true });
  body(s, "Key learning: careful data preparation matters as much as the model, and every prediction should come with evidence.", 0.9, 4.65, 7.0, 1.0, 15.5, { color: H.grey });
  s.addText("THANK YOU  •  QUESTIONS?", { x: 0.9, y: 5.75, w: 7, h: 0.5, fontSize: 20, bold: true, color: H.pink, margin: 0, charSpacing: 2, isTextBox: true, fontFace: "Arial" });
  card(s, 8.45, 1.75, 4.25, 4.8, H.lblue);
  s.addShape(pres.shapes.OVAL, { x: 9.15, y: 2.2, w: 2.85, h: 2.85, fill: { color: H.white }, line: { color: H.blue, width: 2.5 }, objectName: "logo-ring" });
  img(s, "outr_logo_round.png", 9.3, 2.35, 2.55, 2.55, { alt: "OUTR logo" });
  s.addText("Odisha University of Technology and Research, Bhubaneswar", { x: 8.7, y: 5.3, w: 3.75, h: 0.9, fontSize: 14, bold: true, color: H.ink, align: "center", margin: 0, isTextBox: true });
}

// ======================= 25. REFERENCES =======================
{
  const s = content("References", "References (IEEE style)");
  const refs = [
    "J. Cheng et al., “Enhanced performance of brain tumor classification via tumor region augmentation and partition,” PLoS ONE, vol. 10, no. 10, 2015.",
    "P. Afshar, A. Mohammadi, K. N. Plataniotis, “Brain tumor type classification via capsule networks,” in Proc. IEEE ICIP, 2018, pp. 3129–3133.",
    "Z. N. K. Swati et al., “Brain tumor classification for MR images using transfer learning and fine-tuning,” Comput. Med. Imaging Graph., vol. 75, pp. 34–46, 2019.",
    "S. Deepak, P. M. Ameer, “Brain tumor classification using deep CNN features via transfer learning,” Comput. Biol. Med., vol. 111, 103345, 2019.",
    "M. M. Badža, M. Č. Barjaktarović, “Classification of brain tumors from MRI images using a CNN,” Appl. Sci., vol. 10, no. 6, 1999, 2020.",
    "S. Bhuvaji et al., “Brain Tumor Classification (MRI),” Kaggle, 2020, doi: 10.34740/KAGGLE/DSV/1183165.",
    "J. Cheng, “Brain tumor dataset,” Figshare, 2017, doi: 10.6084/m9.figshare.1512427.v5.",
    "M. Tan, Q. V. Le, “EfficientNet: Rethinking model scaling for CNNs,” in Proc. ICML, 2019, pp. 6105–6114.",
    "J. Hu, L. Shen, G. Sun, “Squeeze-and-Excitation networks,” in Proc. IEEE CVPR, 2018, pp. 7132–7141.",
    "O. Ronneberger, P. Fischer, T. Brox, “U-Net: Convolutional networks for biomedical image segmentation,” in Proc. MICCAI, 2015, pp. 234–241.",
    "O. Oktay et al., “Attention U-Net: Learning where to look for the pancreas,” in Proc. MIDL, 2018.",
    "R. R. Selvaraju et al., “Grad-CAM: Visual explanations from deep networks,” in Proc. IEEE ICCV, 2017, pp. 618–626.",
    "A. Chattopadhyay et al., “Grad-CAM++: Generalized gradient-based visual explanations,” in Proc. IEEE WACV, 2018, pp. 839–847.",
    "P. Y. Wen et al., “Updated response assessment criteria for high-grade gliomas: RANO,” J. Clin. Oncol., vol. 28, no. 11, pp. 1963–1972, 2010.",
  ];
  card(s, 0.6, 1.7, 12.1, 5.0, H.white);
  s.addText(refs.map((r, i) => ({ text: `[${i + 1}]  ${r}`, options: { breakLine: i < refs.length - 1 } })),
    { x: 0.85, y: 1.85, w: 11.6, h: 4.7, fontSize: 13, color: H.ink, margin: 0, valign: "top", paraSpaceAfter: 3, isTextBox: true });
}

(async () => {
  await pres.writeFile({ fileName: OUTF });
  await applyTheme(OUTF, THEME);
  console.log("wrote", OUTF, slideNo, "slides");
})();
