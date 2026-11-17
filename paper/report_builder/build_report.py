"""Builds the final B.Tech project report (DOCX + PDF) from results/metrics.json and figs/.
usage: python build_report.py <root_dir_with_results_and_figs> <out_dir>
Two passes: pass 1 renders to PDF to discover page numbers for Contents / List of Figures / List of Tables.
"""
import json, os, sys, subprocess, re, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Report, Pt, Cm, WD_ALIGN_PARAGRAPH
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp"))
from equations import EQ

ROOT = sys.argv[1] if len(sys.argv) > 1 else ".."
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"
os.makedirs(OUT, exist_ok=True)
FIG = lambda n: os.path.join(ROOT, "figs", n)
M = json.load(open(os.path.join(ROOT, "results", "metrics.json")))
SEG = json.load(open(os.path.join(ROOT, "results", "segmentation.json"))) if os.path.exists(os.path.join(ROOT, "results", "segmentation.json")) else None
C, D, S, L = M["classical"], M["deep"], M["split"], M["leakage"]
pc = lambda v: f"{100 * v:.2f}%"
p1 = lambda v: f"{100 * v:.1f}"
f3 = lambda v: f"{v:.3f}"
E, Cn, Sn = D["effb0_clean"], D["cnn_clean"], D["secnn_clean"]
EO = D.get("effb0_official")
CLS = ["No tumor", "Glioma", "Meningioma", "Pituitary"]
best_cls = max(["SVM (RBF)", "Random Forest", "k-NN", "Logistic Regression"], key=lambda k: C[k]["accuracy"])
seg = lambda k, fmt="{:.3f}": (fmt.format(SEG[k]) if SEG and k in SEG else "[TBD]")
TITLE = "Brain Tumor Detection and Monitoring Using Artificial Intelligence and Machine Learning"
RUN = "BRAIN TUMOR DETECTION AND MONITORING USING AI AND ML"
UNI = "ODISHA UNIVERSITY OF TECHNOLOGY AND RESEARCH, BHUBANESWAR, ODISHA"
LOGO = FIG("outr_logo.jpg")


def build(pages):
    R = Report()
    pg = lambda k: str(pages.get(k, ""))

    # ======================= TITLE PAGE =======================
    R.first = False
    R.para("**PROJECT REPORT ON**", "center", 14, before=6, after=18)
    R.para("**“BRAIN TUMOR DETECTION AND MONITORING USING ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING”**", "center", 17, after=14, spacing=1.25)
    p = R.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(LOGO, width=Cm(4.8))
    R.para("*Submitted in partial fulfillment of the requirements for the award of the degree of*", "center", 12, before=10, after=8)
    R.para("**Bachelor of Technology**", "center", 15, after=4)
    R.para("in", "center", 12, after=2)
    R.para("**Computer Science and Engineering (AI & ML)**", "center", 14, after=20)
    R.para("Submitted by", "center", 12, after=4)
    R.para("**CHINMAYEE PATRA** (Regd. No. 23110206)", "center", 13, after=2)
    R.para("**SHRUTI SAMEEKSHYA DEHURY** (Regd. No. 23110234)", "center", 13, after=16)
    R.para("Department of Computer Science and Engineering (AI & ML)", "center", 12, after=16)
    R.para("Under the guidance of", "center", 12, after=2)
    R.para("**Mrs. Swarna Lata Pati**", "center", 14, after=2)
    R.para("Assistant Professor, School of Computer Science", "center", 12, after=16)
    R.para("**Odisha University of Technology and Research**", "center", 13, after=2)
    R.para("Bhubaneswar, Odisha – 751029", "center", 12, after=2)
    R.para("November 2026", "center", 12)

    def letterhead():
        R.para(RUN, "center", 9, after=4).paragraph_format.page_break_before = True
        R.para(f"**{UNI}**", "center", 13, after=6)
        p = R.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(LOGO, width=Cm(3.6))

    def two_signatures(left, right):
        t = R.d.add_table(rows=2, cols=2)
        for ci, (a, b) in enumerate([left, right]):
            c = t.cell(0, ci).paragraphs[0]; c.alignment = WD_ALIGN_PARAGRAPH.CENTER; R.runs(c, f"**{a}**", 12)
            c = t.cell(1, ci).paragraphs[0]; c.alignment = WD_ALIGN_PARAGRAPH.CENTER; R.runs(c, b, 11)

    # ======================= CERTIFICATE =======================
    letterhead()
    h = R.d.add_heading(level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER; R.runs(h, "CERTIFICATE")
    R.para(f"This is to certify that the project report entitled “**{TITLE}**” is a bonafide work carried out jointly by **CHINMAYEE PATRA** "
           "(Registration No. 23110206) and **SHRUTI SAMEEKSHYA DEHURY** (Registration No. 23110234), in partial fulfillment of the requirements for the award of the "
           "degree of **Bachelor of Technology in Computer Science and Engineering (AI & ML)** at Odisha University of Technology and Research (OUTR), Bhubaneswar.")
    R.para("The matter embodied in this project report has been carried out by the students under my supervision and guidance. The work presented herein has not "
           "been submitted elsewhere for the award of any other degree, diploma, or academic certificate.", after=60)
    two_signatures(("Mrs. Swarna Lata Pati", "Assistant Professor (Guide)\nSchool of Computer Science"), ("Dr. Ranjan Kumar Dash", "Head of School, H.O.S (SCS)"))

    # ======================= ACKNOWLEDGEMENT =======================
    letterhead()
    h = R.d.add_heading(level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER; R.runs(h, "ACKNOWLEDGEMENT")
    R.para("We would like to express our profound gratitude and sincere respect to our project guide, **Mrs. Swarna Lata Pati**, Assistant Professor, School of "
           "Computer Science, Odisha University of Technology and Research (OUTR), Bhubaneswar, for her invaluable guidance, inspiring suggestions and constant support "
           f"throughout the development and documentation of this project entitled “{TITLE}.” Her feedback on dataset preparation, model evaluation and "
           "explainable AI shaped the direction of this work.")
    R.para("We extend our sincere thanks to Dr. Chinmayee Pati and Dr. Subhalaxmi Das, Departmental Seminar Coordinators, for their constructive advice and "
           "academic encouragement. We are deeply grateful to **Dr. Ranjan Kumar Dash**, Head of School (SCS), for providing the necessary departmental infrastructure, "
           "and to Prof. (Dr.) Bibhuti Bhusan Biswal, Officer on Special Duty (OSD), OUTR Bhubaneswar, for maintaining an encouraging academic atmosphere.")
    R.para("We also acknowledge the researchers who released the public MRI datasets used in this project, and the open-source communities behind PyTorch, "
           "scikit-learn, OpenCV and FastAPI. Finally, we thank our faculty members, laboratory staff, parents and friends for their encouragement.", after=50)
    two_signatures(("Chinmayee Patra", "Regd. No. 23110206"), ("Shruti Sameekshya Dehury", "Regd. No. 23110234"))

    # ======================= DECLARATION =======================
    letterhead()
    h = R.d.add_heading(level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER; R.runs(h, "DECLARATION")
    R.para("We hereby certify that:")
    R.bullets(["The work contained in this project report is original and has been carried out by us under the general supervision of Mrs. Swarna Lata Pati.",
               "The work has not been submitted to any other Institute or University for the award of any degree or diploma.",
               "We have followed the guidelines and formatting protocols provided by the Institute in preparing this report.",
               "All public datasets, algorithms, figures and text taken from external sources have been credited by citing them in the text and listing them in the References section.",
               "All experimental results reported in this document were produced by our own code on the stated public datasets and can be reproduced with the scripts in the project repository."], numbered=True)
    R.para("", after=40)
    two_signatures(("Chinmayee Patra", "Regd. No. 23110206"), ("Shruti Sameekshya Dehury", "Regd. No. 23110234"))

    # ======================= ABSTRACT =======================
    R.front_heading("ABSTRACT")
    R.para("Brain tumours are among the most serious diseases of the central nervous system, and Magnetic Resonance Imaging (MRI) is the standard tool for detecting "
           "and following them. Reading MRI slices manually is slow and depends on the experience of the radiologist, which motivates computer-aided decision support. "
           "This project designs, trains and evaluates a complete machine-learning pipeline for **four-class brain tumour classification** (no tumour, glioma, "
           "meningioma and pituitary tumour) on a **publicly available MRI dataset**, and wraps the trained models in a web application with visual explanations, "
           "tumour measurement and a follow-up comparison module.", indent=True, spacing=1.3)
    R.para(f"Before training, we audited the public dataset and found that **{L['official_test_near_dup']} of its {L['n_test']} official test images "
           f"({100 * L['official_test_near_dup'] / L['n_test']:.0f}%) are near-duplicates of training images**. We therefore removed duplicates and built a leakage-free, "
           f"stratified 70/15/15 split of {S['unique_images_kept']:,} unique images. On this split we compare classical machine learning on Histogram of Oriented "
           f"Gradients (HOG) features (SVM, Random Forest, k-NN, Logistic Regression), a custom Convolutional Neural Network (CNN) trained from scratch, the same CNN "
           f"with Squeeze-and-Excitation (SE) blocks, and an ImageNet-pretrained EfficientNet-B0 fine-tuned by transfer learning. The best classical model, "
           f"HOG + SVM, reached {pc(C[best_cls]['accuracy'])} test accuracy, the custom CNN {pc(Cn['accuracy'])}, the SE-CNN {pc(Sn['accuracy'])}, and "
           f"EfficientNet-B0 achieved the best result with **{pc(E['accuracy'])} accuracy, macro F1 of {E['macro_f1']:.3f} and macro ROC-AUC of "
           f"{E['roc_auc_ovr_macro']:.3f}** on {S['split_sizes']['test']} unseen test images." + (
               f" Evaluated on the original (leaky) split, the same network scored {pc(EO['accuracy'])}, showing how duplicate leakage inflates reported results." if EO else ""), indent=True, spacing=1.3)
    R.para("Grad-CAM and Grad-CAM++ heatmaps are generated for every prediction so that the user can check whether the model looked at the lesion. A U-Net and an "
           f"Attention U-Net trained on the Figshare tumour-mask dataset provide tumour outlines" + (f" (test Dice {SEG['unet_dice']:.3f} and {SEG['attunet_dice']:.3f})" if SEG else "") + ", from which the system measures tumour area and diameters and compares "
           "a baseline scan with a follow-up scan using RANO-inspired thresholds. The system is delivered as a FastAPI web application with PDF report generation. "
           "The work is an academic decision-support prototype and is not intended for clinical diagnosis.", indent=True, spacing=1.3)
    R.para("**Keywords:** Brain Tumour Classification, MRI, Machine Learning, Support Vector Machine, Convolutional Neural Network, Transfer Learning, EfficientNet, "
           "Squeeze-and-Excitation, U-Net, Grad-CAM, Data Leakage, Explainable AI.", before=6)
    two_signatures(("Signature of Guide", ""), ("Signature of Students", ""))

    # ======================= CONTENTS =======================
    R.front_heading("CONTENTS")
    for t, k in [("TITLE PAGE", "title"), ("CERTIFICATE", "CERTIFICATE"), ("ACKNOWLEDGEMENT", "ACKNOWLEDGEMENT"), ("DECLARATION", "DECLARATION"), ("ABSTRACT", "ABSTRACT"),
                 ("CONTENTS", "CONTENTS"), ("LIST OF FIGURES", "LIST OF FIGURES"), ("LIST OF TABLES", "LIST OF TABLES")]:
        R.toc_line(t, pages.get(k, 1 if k == "title" else ""))
    R.para("**CHAPTERS**", "left", before=6, after=3)
    for i, t in enumerate(CHAPTERS, 1):
        R.toc_line(f"CHAPTER {i} – {t.upper()}", pg(f"CH{i}"), indent=0.4, size=11.5)
    R.toc_line("REFERENCES", pg("REFERENCES"))

    R.front_heading("LIST OF FIGURES")
    for k, f in enumerate(pages.get("_figs", []), 1):
        R.toc_line(f, pg(f"F{k}"), size=10.5)
    R.front_heading("LIST OF TABLES")
    for k, f in enumerate(pages.get("_tabs", []), 1):
        R.toc_line(f, pg(f"T{k}"), size=10.5)

    # ======================= CHAPTER 1 =======================
    R.chapter_heading(CHAPTERS[0])
    R.section("Background")
    R.para("Brain and other central nervous system (CNS) tumours are abnormal growths of cells inside the skull. According to GLOBOCAN 2022 estimates, more than "
           "320,000 new cases of brain and CNS cancer and roughly 250,000 deaths occur worldwide each year [1]. Because the skull is a closed space, even a slowly "
           "growing tumour can press on vital structures, so early and accurate detection directly influences treatment choices such as surgery, radiotherapy and "
           "chemotherapy.", indent=True)
    R.para("In routine practice, a radiologist inspects dozens of MRI slices per patient. This manual reading is time-consuming, can be affected by fatigue, and "
           "different readers may disagree on borderline cases. Computer-aided detection (CAD) tools that classify and localise tumours automatically can act as a "
           "second reader and speed up triage.", indent=True)
    R.section("Role of MRI in Brain Tumour Diagnosis")
    R.para("Magnetic Resonance Imaging is the preferred modality for brain tumours because it gives excellent soft-tissue contrast without ionising radiation. "
           "T1-weighted images show anatomy; gadolinium contrast-enhanced T1 (T1-CE) highlights regions where the blood–brain barrier is broken, which is typical "
           "of many tumours; T2-weighted and FLAIR sequences reveal oedema around the lesion. The public datasets used in this project consist mainly of 2D slices "
           "from such sequences, which is why the system works on individual slices.", indent=True)
    R.section("Machine Learning and Deep Learning in Medical Imaging")
    R.para("Classical machine-learning pipelines first convert an image into a hand-crafted feature vector (for example texture or gradient histograms) and then "
           "train a classifier such as a Support Vector Machine. Deep learning, in particular the Convolutional Neural Network (CNN), learns the features directly from "
           "pixels by stacking convolution, non-linearity and pooling layers. With transfer learning, a CNN pretrained on a large natural-image dataset (ImageNet) can "
           "be fine-tuned on a few thousand medical images, which suits the limited size of public MRI datasets. This project implements and compares both families.", indent=True)
    R.section("Need for Explainable AI")
    R.para("A prediction such as “glioma, 97%” is not enough for a clinician: they need to see *why* the model decided so. Explainable AI (XAI) methods such "
           "as Grad-CAM produce a heatmap of the image regions that most influenced the decision. If the heatmap falls on the lesion, trust increases; if it falls on "
           "the skull or on image text, the prediction should be treated with suspicion. XAI is therefore built into every prediction made by our system.", indent=True)
    R.section("Problem Statement")
    R.para("To design, implement and honestly evaluate a brain-MRI analysis system that (i) classifies a 2D MRI slice into no tumour, glioma, meningioma or pituitary "
           "tumour using machine-learning and CNN models trained on a public dataset; (ii) explains each prediction with Grad-CAM and Grad-CAM++ heatmaps; (iii) segments "
           "the tumour to measure its size; and (iv) compares two scans of the same patient to indicate response or progression, all through an easy-to-use web interface.", indent=True)
    R.section("Motivation")
    R.para("Many student projects and even published papers report near-perfect accuracy on public brain-MRI datasets. While preparing this project we found that a "
           "large fraction of the official test images in a widely used dataset also appear in its training folder. Results obtained on such a split overestimate how "
           "the model would perform on new patients. A key motivation of this work is therefore to follow a careful, reproducible evaluation protocol and to compare "
           "simple and advanced models on equal terms.", indent=True)
    R.section("Objectives of the Project")
    R.bullets(["To collect a publicly available brain-tumour MRI dataset, audit it for duplicate images and label conflicts, and build a leakage-free train/validation/test split.",
               "To design a preprocessing pipeline (brain cropping, CLAHE contrast enhancement, resizing, normalisation and data augmentation).",
               "To implement classical machine-learning baselines (HOG features with SVM, Random Forest, k-NN and Logistic Regression).",
               "To design a custom CNN, extend it with Squeeze-and-Excitation blocks, and fine-tune an ImageNet-pretrained EfficientNet-B0 using transfer learning.",
               "To evaluate all models with accuracy, precision, recall, F1-score, ROC-AUC and confusion matrices on the same unseen test set.",
               "To explain predictions with Grad-CAM and Grad-CAM++, and to segment tumours with U-Net and Attention U-Net for area and diameter measurement.",
               "To deploy the trained models in a FastAPI web application with follow-up comparison and PDF report generation."], numbered=True)
    R.section("Organisation of the Report")
    R.para("Chapter 2 reviews the background and related work. Chapter 3 describes the datasets, the leakage audit and preprocessing. Chapter 4 explains the models "
           "and training procedure. Chapter 5 covers explainable AI. Chapter 6 presents the experimental results. Chapter 7 describes tumour measurement, follow-up "
           "monitoring and the software implementation. Chapter 8 discusses advantages, limitations and future scope, and Chapter 9 concludes the report.", indent=True)

    # ======================= CHAPTER 2 =======================
    R.chapter_heading(CHAPTERS[1])
    R.section("Brain Tumour Types Considered")
    R.para("**Gliomas** arise from glial cells and range from slow-growing low-grade tumours to aggressive glioblastoma; they are intra-axial (inside the brain tissue) and "
           "often have irregular, infiltrative borders. **Meningiomas** grow from the meninges covering the brain; they are usually benign, extra-axial and well "
           "circumscribed. **Pituitary tumours** (mostly adenomas) occur in the sella turcica at the skull base and may affect hormones or vision. The fourth class, "
           "**no tumour**, contains normal slices. The WHO 2021 classification [2] further subdivides these groups using molecular markers, which is beyond the scope "
           "of image-only classification.", indent=True)
    R.section("Classical Machine Learning for Image Classification")
    R.para("In a classical pipeline the image is described by features. The **Histogram of Oriented Gradients (HOG)** [3] divides the image into small cells, computes "
           "the gradient magnitude and orientation at every pixel, and builds a histogram of orientations per cell; neighbouring cells are normalised together in "
           "blocks. The feature vector is then classified by algorithms such as the **Support Vector Machine (SVM)** [4], which finds the maximum-margin boundary "
           "between classes, the **Random Forest** [5], an ensemble of decision trees trained on bootstrap samples, **k-Nearest Neighbours**, which votes among the "
           "closest training samples, and **Logistic Regression**, a linear probabilistic classifier.", indent=True)
    R.section("Convolutional Neural Networks")
    R.para("A CNN learns filters (kernels) that slide over the image. Early layers detect edges and textures; deeper layers combine them into shapes and "
           "lesion-like patterns. Batch Normalisation stabilises training, ReLU adds non-linearity, max pooling reduces spatial size, and a final fully connected "
           "layer with softmax produces class probabilities. Training minimises a cross-entropy loss with back-propagation and a gradient-based optimiser such as Adam [6].", indent=True)
    R.section("Transfer Learning and EfficientNet")
    R.para("Transfer learning reuses a network trained on ImageNet (1.28 million natural images) as the starting point. **EfficientNet** [7] scales network depth, width "
           "and input resolution together using a compound coefficient; its smallest member, EfficientNet-B0, has about 4 million parameters and is built from "
           "mobile inverted bottleneck (MBConv) blocks that already contain Squeeze-and-Excitation units. Its small size makes it practical to fine-tune on a CPU or a laptop GPU.", indent=True)
    R.section("Squeeze-and-Excitation Networks")
    R.para("Hu *et al.* [8] proposed the Squeeze-and-Excitation (SE) block, which learns how important each feature channel is. It “squeezes” every channel to "
           "a single number by global average pooling, passes the vector through two small fully connected layers, and multiplies the original channels by the "
           "resulting weights. We add SE blocks to our custom CNN and measure their effect experimentally (Chapter 6).", indent=True)
    R.section("Segmentation Networks: U-Net and Attention U-Net")
    R.para("**U-Net** [9] is an encoder–decoder network with skip connections that copy high-resolution features from the encoder to the decoder, enabling pixel-level "
           "masks from few training images. **Attention U-Net** [10] adds attention gates on the skip connections so that features from irrelevant regions (skull, "
           "healthy tissue) are suppressed before being merged in the decoder.", indent=True)
    R.section("Explainable AI")
    R.para("Grad-CAM [11] weights the feature maps of the last convolutional layer by the average gradient of the class score and keeps the positive part. "
           "Grad-CAM++ [12] uses higher-order gradient terms to weight individual pixels, which often gives tighter maps and handles multiple lesions better.", indent=True)
    R.section("Related Work")
    R.para("Table 1 summarises representative studies on brain-tumour MRI classification. Most report results on the Figshare dataset of Cheng *et al.* [13] (three tumour "
           "classes, no normal class); numbers are therefore not directly comparable with our four-class, leakage-free setting.", indent=True)
    R.table("Representative related work on brain-tumour MRI classification", ["Study", "Method", "Dataset", "Reported result"],
            [["Cheng et al. (2015) [14]", "Tumour-region augmentation + BoW features + SVM", "Figshare, 3 classes", "91.28% accuracy"],
             ["Afshar et al. (2019) [15]", "Capsule network (CapsNet)", "Figshare, 3 classes", "90.89% accuracy"],
             ["Deepak & Ameer (2019) [16]", "GoogLeNet transfer learning (+ SVM / KNN)", "Figshare, 3 classes", "97.1% mean accuracy"],
             ["Swati et al. (2019) [17]", "VGG-19 block-wise fine-tuning", "Figshare, 3 classes", "94.82% accuracy"],
             ["Badža & Barjaktarović (2020) [18]", "Custom CNN, 10-fold cross-validation", "Figshare, 3 classes", "96.56% accuracy"],
             ["Ronneberger et al. (2015) [9]", "U-Net (segmentation)", "Cell microscopy (ISBI)", "Segmentation benchmark winner"]],
            [4.0, 5.6, 3.2, 3.2], align=["left", "left", "center", "center"])
    R.section("Research Gaps")
    R.bullets(["Many works split the data at image level, so slices of the same patient or duplicate images can appear in both training and test sets, inflating accuracy.",
               "Few studies compare simple classical baselines and deep models under one identical protocol.",
               "Explainability is often shown for a handful of hand-picked images rather than integrated in the prediction workflow.",
               "Segmentation, measurement and follow-up comparison are rarely combined with classification in one usable tool."])
    R.para("This project addresses these gaps with a de-duplicated split, a side-by-side model comparison, XAI for every prediction and an integrated web application.", indent=True)

    # ======================= CHAPTER 3 =======================
    R.chapter_heading(CHAPTERS[2])
    R.section("Datasets Used")
    R.para("**Classification dataset.** We use the *Brain Tumor Classification (MRI)* dataset released by Bhuvaji *et al.* [19] on Kaggle and mirrored on GitHub. It contains "
           f"3,264 JPEG slices in four folders: glioma (926), meningioma (937), pituitary (901) and no tumour (500), already divided into an official *Training* "
           "(2,870) and *Testing* (394) folder. Images come from different sources and have different sizes (most are 512×512).", indent=True)
    R.para("**Segmentation dataset.** For tumour outlines we use the Figshare dataset of Cheng *et al.* [13]: 3,064 T1-CE slices from 233 patients (708 meningioma, "
           "1,426 glioma, 930 pituitary) with expert-drawn binary tumour masks. Because patient identifiers are provided, the segmentation split is done at **patient "
           "level**, so no patient appears in more than one subset.", indent=True)
    R.figure(FIG("fig_samples.png"), "Random examples of the four classes after preprocessing (classification dataset).", 12.5)
    R.section("Data Quality Audit and Leakage Detection")
    R.para("Before training, every image was reduced to a 32×32 thumbnail, mean-centred and L2-normalised, and the cosine similarity between all pairs of images "
           "was computed. Two images with similarity of at least 0.98 were treated as near-duplicates and grouped together with a union–find procedure.", indent=True)
    R.equation(r"\mathrm{sim}(a,b) = \frac{(\mathbf{a}-\bar{a})\cdot(\mathbf{b}-\bar{b})}{\lVert \mathbf{a}-\bar{a}\rVert\,\lVert \mathbf{b}-\bar{b}\rVert} \geq 0.98")
    R.para(f"The audit found {S['images_in_duplicate_clusters']} images belonging to {S['duplicate_clusters']} duplicate groups; {S['clusters_spanning_official_train_test']} groups "
           f"span both the official training and testing folders, and **{L['official_test_near_dup']} of the {L['n_test']} official test images "
           f"({100 * L['official_test_near_dup'] / L['n_test']:.0f}%) have a near-identical copy in the training folder** (Figure {R.fig_n + 1}). "
           f"{S['conflicting_label_clusters']} groups contained the same image under different labels and were removed.", indent=True)
    R.figure(FIG("fig_leakage.png"), "Leakage audit: an official test image and its near-identical copy in the training folder (left); share of official test images that are near-duplicates (right).", 15.5)
    R.section("Leakage-Free Split")
    R.para(f"Keeping one representative per duplicate group leaves {S['unique_images_kept']:,} unique images. These were split 70/15/15 into training, validation and test sets "
           "with stratification by class (scikit-learn *StratifiedGroupKFold*, seed 42). The validation set is used only for model selection and early stopping; the "
           "test set is used once, for the final numbers in Chapter 6.", indent=True)
    sp = S["split_per_class"]
    R.table("Class distribution of the de-duplicated, leakage-free split", ["Subset", "No tumour", "Glioma", "Meningioma", "Pituitary", "Total"],
            [[nm.capitalize()] + sp[nm] + [S["split_sizes"][nm]] for nm in ["train", "val", "test"]] +
            [["Total"] + S["unique_per_class"] + [S["unique_images_kept"]]], [3.0, 2.4, 2.4, 2.6, 2.4, 2.2])
    R.figure(FIG("fig_class_dist.png"), "Images per class before and after de-duplication. The no-tumour class is the minority class.", 12.0)
    R.section("Preprocessing Pipeline")
    R.para(f"Every image passes through the same steps at training and at inference time (Figure {R.fig_n + 1}, Table {R.tab_n + 1}). The brain region is located by Gaussian blurring, "
           "thresholding and morphological erosion/dilation; the bounding box of the largest contour is cropped, which removes empty background and scanner text. "
           "Contrast-Limited Adaptive Histogram Equalisation (CLAHE) then improves local contrast without amplifying noise excessively.", indent=True)
    R.figure(FIG("fig_preprocessing.png"), "Preprocessing steps applied to a real MRI slice from the dataset.", 16.0)
    R.table("Preprocessing steps and parameters", ["Step", "Operation and parameters"],
            [["Grayscale conversion", "RGB/JPEG slice converted to a single 8-bit channel"],
             ["Brain cropping", "Gaussian blur 5×5, threshold 45, erode/dilate ×2, crop largest contour"],
             ["Contrast enhancement", "CLAHE, clip limit 2.0, tile grid 8×8"],
             ["Resizing", "Area interpolation to 128×128 (custom CNN, HOG) or 160×160 (EfficientNet-B0)"],
             ["Normalisation", "Custom CNN: (x/255 − 0.5)/0.25; EfficientNet: gray replicated to 3 channels, ImageNet mean/std"],
             ["Augmentation (train only)", "Horizontal flip, rotation ±10°, scale 0.9–1.1, brightness/contrast jitter ±10%"]],
            [4.4, 11.6], align=["left", "left"])

    # ======================= CHAPTER 4 =======================
    R.chapter_heading(CHAPTERS[3])
    R.section("Overall System Architecture")
    R.para(f"Figure {R.fig_n + 1} shows the complete system. A preprocessed slice is sent to the classification models and to the segmentation network. The classifier returns "
           "class probabilities and Grad-CAM heatmaps; the segmenter returns a tumour mask from which size measurements are computed; two measured scans can be compared "
           f"for follow-up. All outputs are shown in a FastAPI web application, which can also export a PDF report. Figure {R.fig_n + 2} shows the development workflow.", indent=True)
    R.figure(FIG("fig_architecture.png"), "Overall architecture of the proposed brain tumour detection and monitoring system.", 16.0)
    R.figure(FIG("fig_workflow.png"), "Project workflow from data collection to deployment.", 16.0)
    R.section("Classical Machine-Learning Baselines")
    R.para("Each 128×128 image is described by a HOG vector (9 orientation bins, 16×16-pixel cells, 2×2-cell blocks, L2-Hys normalisation), giving "
           f"{C['hog_dim']} features. The gradient magnitude and orientation at every pixel are", indent=True)
    R.equation(EQ["hog"])
    R.figure(FIG("fig_hog.png"), "HOG representation of an MRI slice: each cell stores a histogram of local gradient orientations.", 9.5)
    R.para("Features are standardised and reduced to 150 dimensions by Principal Component Analysis (PCA). The soft-margin SVM solves", indent=True)
    R.equation(EQ["svm"])
    R.para("subject to y~i~(**w**·φ(**x**~i~) + b) ≥ 1 − ξ~i~ and ξ~i~ ≥ 0, using the radial basis function (RBF) kernel", indent=False)
    R.equation(EQ["rbf"])
    R.para("Hyper-parameters (C, γ for SVM; number of trees and depth for Random Forest; k for k-NN; C for Logistic Regression) are selected by grid search on the "
           "validation set; class weights are balanced to compensate for the smaller no-tumour class.", indent=True)
    R.section("CNN Fundamentals")
    R.para("A convolution layer computes, for kernel K and input I,", indent=True)
    R.equation(EQ["conv"])
    R.para("followed by Batch Normalisation and the ReLU activation, ReLU(x) = max(0, x). The last layer outputs logits z~c~ that are converted to probabilities with softmax:", indent=False)
    R.equation(EQ["softmax"])
    R.para("Training minimises a class-weighted cross-entropy with label smoothing, where w~c~ compensates for class imbalance and ε prevents over-confident outputs:", indent=True)
    R.equation(EQ["ce"])
    R.equation(EQ["cw"] + r",\qquad " + EQ["smooth"])
    R.section("Custom CNN and SE-CNN")
    R.para(f"Our custom CNN (Figure {R.fig_n + 1}) has four convolutional blocks with 32, 64, 128 and 256 filters. Each block applies two 3×3 convolutions with Batch "
           f"Normalisation and ReLU, followed by 2×2 max pooling. Global average pooling (GAP) feeds a 128-unit fully connected layer, dropout of 0.4 and a 4-unit "
           f"output layer. The plain CNN has {Cn['params']:,} parameters. The **SE-CNN** adds a Squeeze-and-Excitation block at the end of every convolutional block "
           f"({Sn['params']:,} parameters), allowing a direct ablation of channel attention.", indent=True)
    R.figure(FIG("fig_cnn.png"), "Custom CNN architecture (SE blocks present only in the SE-CNN variant).", 16.0)
    R.para("The SE block squeezes each channel to its spatial mean and then learns channel weights with two fully connected layers (reduction ratio r = 8):", indent=True)
    R.equation(EQ["squeeze"])
    R.equation(EQ["excite"])
    R.para(f"where δ is ReLU and σ the sigmoid function (Figure {R.fig_n + 1}).", indent=False)
    R.figure(FIG("fig_se.png"), "Squeeze-and-Excitation block.", 14.5)
    R.section("Transfer Learning with EfficientNet-B0")
    R.para(f"EfficientNet-B0 (Figure {R.fig_n + 1}) is initialised with ImageNet weights, its 1000-class head is replaced by a 4-class layer, and the whole network "
           f"({E['params']:,} parameters) is fine-tuned. Grayscale slices are replicated to three channels and normalised with the ImageNet mean and standard deviation.", indent=True)
    R.figure(FIG("fig_effnet.png"), "EfficientNet-B0 transfer-learning architecture used for classification.", 16.0)
    R.section("Training Configuration")
    R.table("Training hyper-parameters of the deep models", ["Setting", "Custom CNN / SE-CNN", "EfficientNet-B0"],
            [["Input", "1×128×128", "3×160×160"], ["Initial weights", "Random (He)", "ImageNet"],
             ["Optimiser", "AdamW, weight decay 1e-4", "AdamW, weight decay 1e-4"], ["Learning-rate schedule", "One-cycle, max 2e-3", "One-cycle, max 1e-3"],
             ["Epochs / batch size", f"{Cn['epochs']} / 32", f"{E['epochs']} / 32"], ["Loss", "Weighted CE, label smoothing 0.05", "Weighted CE, label smoothing 0.05"],
             ["Model selection", "Best validation accuracy", "Best validation accuracy"], ["Random seed", "42", "42"]],
            [4.6, 5.7, 5.7], align=["left", "left", "left"])
    R.section("Segmentation with U-Net and Attention U-Net")
    R.para(f"For tumour outlines we use a four-level U-Net and an Attention U-Net (Figure {R.fig_n + 1}) trained on the Figshare masks at 256×256. Each attention gate receives "
           "the encoder feature x and a gating signal g from the coarser decoder level:", indent=True)
    R.figure(FIG("fig_unet.png"), "Attention U-Net with attention gates (AG) on the skip connections.", 14.5)
    R.equation(EQ["ag"])
    R.para("and the skip feature is multiplied by α before concatenation. Because tumour pixels are a small fraction of each slice, the loss combines binary "
           "cross-entropy with the soft Dice loss:", indent=False)
    R.equation(EQ["segloss"])

    # ======================= CHAPTER 5 =======================
    R.chapter_heading(CHAPTERS[4])
    R.para("Explainability is part of every prediction in our system. This chapter describes the two gradient-based methods used and shows their output on unseen test images.", indent=True)
    R.section("Grad-CAM")
    R.para("Let A^k^ be the k-th feature map of the last convolutional layer (the 1280-channel 1×1 convolution of EfficientNet-B0) and y^c^ the score of class c. "
           "Grad-CAM computes a weight for each map by global-average-pooling its gradient and then combines the maps:", indent=True)
    R.equation(EQ["gc_w"])
    R.equation(EQ["gc_map"])
    R.para("The map is up-sampled to the input size and overlaid on the slice. ReLU keeps only regions that increase the class score.", indent=True)
    R.section("Grad-CAM++")
    R.para("Grad-CAM++ replaces the uniform average by pixel-wise weights obtained from higher-order derivatives; with an exponential score function these reduce to", indent=True)
    R.equation(EQ["gcpp"])
    R.para("and the channel weight becomes α~k~^c^ = Σ~i,j~ w~ij~^kc^ · ReLU(∂y^c^/∂A~ij~^k^). Pixels that contribute strongly receive more weight, "
           "giving sharper maps, especially when several regions are relevant.", indent=False)
    R.section("Qualitative Results")
    R.figure(FIG("fig_gradcam.png"), "Grad-CAM and Grad-CAM++ for correctly classified test images of each class (EfficientNet-B0).", 14.5)
    R.para("In the glioma example the strongest activation lies over the hemisphere containing the lesion, and in the pituitary example it is centred on the "
           "sella region at the skull base, which is where pituitary tumours occur. For the meningioma and no-tumour examples the activation is broad and covers "
           "most of the brain. Grad-CAM++ is slightly more compact than Grad-CAM but follows the same pattern. Because the last convolutional layer of "
           "EfficientNet-B0 has only 5\u00d75 positions at 160\u00d7160 input, the maps are coarse: they show the region the network relied on, not the tumour "
           "boundary, which is why a separate segmentation network is used for outlines and measurements.", indent=True)
    R.section("Using Heatmaps for Error Analysis")
    R.figure(FIG("fig_errors.png"), "Examples of misclassified test images with their Grad-CAM++ maps.", 11.5)
    R.para(f"Heatmaps also help to understand mistakes (Figure {R.fig_n}). In some misclassified images the lesion looks more like the predicted class than "
           "the given label, for example a midline sellar mass labelled as glioma and predicted as pituitary tumour, or a round, dural-based lesion labelled as "
           "glioma and predicted as meningioma. This suggests that part of the remaining error may come from label noise in the public dataset, although this "
           "cannot be confirmed without the original radiology reports. In other errors the activation is spread out without a clear focus, which signals low reliability.", indent=True)
    R.section("Limitations of Saliency Maps")
    R.para("Gradient-based maps can be sensitive to the chosen layer and do not prove causality. They are used here as a visual sanity check, not as a diagnostic tool.", indent=True)

    # ======================= CHAPTER 6 =======================
    R.chapter_heading(CHAPTERS[5])
    R.section("Experimental Setup")
    R.para(f"All models were trained and evaluated on the same de-duplicated split ({S['split_sizes']['train']} training, {S['split_sizes']['val']} validation and "
           f"{S['split_sizes']['test']} test images). The reference run used Python 3, PyTorch, timm and scikit-learn on a 2-core CPU; the code also runs on CUDA "
           "and Apple-Silicon (MPS) GPUs. The test set was used only once per model.", indent=True)
    R.section("Evaluation Metrics")
    R.para("With TP, TN, FP and FN denoting true/false positives/negatives for a class (one-vs-rest), we report:", indent=True)
    R.equation(EQ["acc"])
    R.equation(EQ["prec"])
    R.equation(EQ["f1"])
    R.para("Macro averages give every class equal weight, which is important because the no-tumour class is smaller. ROC-AUC (area under the receiver operating "
           "characteristic curve) measures ranking quality independent of the decision threshold.", indent=True)
    R.section("Classification Results")
    rows = []
    for k in ["Logistic Regression", "k-NN", "Random Forest", "SVM (RBF)"]:
        r = C[k]; rows.append([f"HOG + {k}", pc(r["accuracy"]), f3(r["macro_precision"]), f3(r["macro_recall"]), f3(r["macro_f1"]), f3(r["roc_auc_ovr_macro"])])
    for k, nm in [("cnn_clean", "Custom CNN (scratch)"), ("secnn_clean", "SE-CNN (scratch)"), ("effb0_clean", "**EfficientNet-B0 (transfer)**")]:
        r = D[k]; rows.append([nm, pc(r["accuracy"]), f3(r["macro_precision"]), f3(r["macro_recall"]), f3(r["macro_f1"]), f3(r["roc_auc_ovr_macro"])])
    R.table(f"Test-set performance of all models (n = {S['split_sizes']['test']}, leakage-free split)", ["Model", "Accuracy", "Macro precision", "Macro recall", "Macro F1", "ROC-AUC"],
            rows, [5.0, 2.2, 2.3, 2.2, 2.1, 2.2])
    R.figure(FIG("fig_comparison.png"), "Accuracy and macro F1 of classical and deep models on the same test set.", 15.5)
    ordered = sorted([(k, C[k]["accuracy"]) for k in ["Logistic Regression", "k-NN", "Random Forest"]], key=lambda t: -t[1])
    R.para(f"Table {R.tab_n} and Figure {R.fig_n} show a clear progression. Among classical models, the RBF-SVM on HOG features is the strongest ({pc(C['SVM (RBF)']['accuracy'])}), "
           f"followed by {ordered[0][0]} ({pc(ordered[0][1])}), {ordered[1][0]} ({pc(ordered[1][1])}) and {ordered[2][0]} ({pc(ordered[2][1])}). "
           f"The custom CNN trained from scratch reaches {pc(Cn['accuracy'])} and the SE-CNN {pc(Sn['accuracy'])}"
           + (f", i.e. channel attention changed accuracy by {100 * (Sn['accuracy'] - Cn['accuracy']):+.2f} percentage points. " if True else ". ")
           + f"Transfer learning gives the largest gain: EfficientNet-B0 reaches **{pc(E['accuracy'])}** accuracy and a macro ROC-AUC of **{E['roc_auc_ovr_macro']:.3f}**, "
           f"confirming that ImageNet features transfer well to MRI when the dataset contains only a few thousand images.", indent=True)
    R.section("Training Behaviour")
    R.figure(FIG("fig_curves.png"), "Training and validation loss/accuracy of the three deep models.", 16.0)
    R.para("EfficientNet-B0 converges within a few epochs because it starts from pretrained features, whereas the scratch CNNs need more epochs and show larger "
           "validation fluctuations. The small gap between training and validation curves, helped by augmentation, dropout and label smoothing, indicates limited over-fitting.", indent=True)
    R.section("Per-Class Analysis")
    pcR = E["per_class"]
    R.table("Per-class results of EfficientNet-B0 on the test set", ["Class", "Precision", "Recall (sensitivity)", "F1-score", "Test images"],
            [[CLS[i], f3(pcR["precision"][i]), f3(pcR["recall"][i]), f3(pcR["f1"][i]), sum(E["confusion"][i])] for i in range(4)], [3.6, 2.8, 3.6, 2.8, 2.8])
    R.figure(FIG("fig_confusion.png"), "Confusion matrices of the best classical model (HOG + SVM) and the best deep model (EfficientNet-B0).", 15.5)
    worst = int(min(range(4), key=lambda i: pcR["recall"][i]))
    cm = E["confusion"]; offd = max(((i, j) for i in range(4) for j in range(4) if i != j), key=lambda t: cm[t[0]][t[1]])
    R.para(f"The most frequent confusion of EfficientNet-B0 is {CLS[offd[0]].lower()} predicted as {CLS[offd[1]].lower()} ({cm[offd[0]][offd[1]]} images), and the "
           f"lowest recall is for the {CLS[worst].lower()} class ({pc(pcR['recall'][worst])}). Gliomas and meningiomas can look similar on a single contrast-enhanced "
           "slice, and some no-tumour images in this dataset come from different scanners and orientations, which makes them harder to recognise.", indent=True)
    R.figure(FIG("fig_roc.png"), "One-vs-rest ROC curves of EfficientNet-B0.", 9.5)
    if EO:
        R.section("Effect of Data Leakage")
        R.para(f"To quantify the leakage problem, EfficientNet-B0 was also trained on the official folders (with 15% of the training folder held out for validation) and "
               f"tested on the official test folder. It scored **{pc(EO['accuracy'])}**, compared with {pc(E['accuracy'])} on our leakage-free split (Figure {R.fig_n + 1}). "
               + ("Because most official test images have a copy in the training folder, the official number partly measures memorisation, not generalisation. "
                  if EO["accuracy"] > E["accuracy"] else
                  "Interestingly, the official test folder is also known to contain images whose distribution differs from the training folder, so the official "
                  "number is affected both by duplicates and by this distribution shift. ")
               + "We therefore report the leakage-free result as our main result.", indent=True)
        R.figure(FIG("fig_split_effect.png"), "Same model, different evaluation split.", 9.5)
    R.section("Segmentation Results")
    R.para("The segmentation networks are evaluated on the patient-level test split of the Figshare dataset with the Dice coefficient and Intersection-over-Union (IoU):", indent=True)
    R.equation(EQ["dice"])
    R.table("Segmentation performance on the Figshare patient-level test split", ["Model", "Dice (mean)", "IoU (mean)", "Parameters"],
            [["U-Net", seg("unet_dice"), seg("unet_iou"), seg("unet_params", "{:,}")], ["Attention U-Net", seg("attunet_dice"), seg("attunet_iou"), seg("attunet_params", "{:,}")]],
            [5.0, 3.4, 3.4, 3.4])
    if SEG:
        pcd = SEG["per_class_dice"]
        R.para(f"On {SEG['n_test_images']} test slices from {SEG['n_test_patients']} unseen patients, the Attention U-Net improves the mean Dice from "
               f"{SEG['unet_dice']:.3f} to {SEG['attunet_dice']:.3f} and the IoU from {SEG['unet_iou']:.3f} to {SEG['attunet_iou']:.3f}, with only "
               f"{(SEG['attunet_params'] - SEG['unet_params']) / 1e3:.0f} thousand extra parameters. Meningiomas, which have sharp borders, are segmented best "
               f"(Dice {pcd['attunet']['meningioma']:.3f}), while infiltrative gliomas remain the hardest (Dice {pcd['attunet']['glioma']:.3f}). The attention gates "
               "help most on small lesions, where the plain U-Net more often produces false positives near the skull.", indent=True)
        R.table("Per-tumour-type Dice on the segmentation test split", ["Model", "Meningioma", "Glioma", "Pituitary"],
                [["U-Net"] + [f"{pcd['unet'][k]:.3f}" for k in ["meningioma", "glioma", "pituitary"]],
                 ["Attention U-Net"] + [f"{pcd['attunet'][k]:.3f}" for k in ["meningioma", "glioma", "pituitary"]]], [5.0, 3.4, 3.4, 3.4])
    if os.path.exists(FIG("fig_segmentation.png")):
        R.figure(FIG("fig_segmentation.png"), "Comparison of ground-truth tumour masks with U-Net and Attention U-Net predictions on held-out patient test slices.", 15.5)
    R.section("Comparison with Literature")
    R.para(f"Published studies in Table 1 report 90–98% accuracy, mostly on the three-class Figshare dataset with image-level splits. Our EfficientNet-B0 result of "
           f"{pc(E['accuracy'])} is obtained on a harder four-class task with a strictly de-duplicated test set; it is therefore a conservative estimate and should not be "
           "ranked directly against those numbers. The more important finding is the relative ordering of models under identical conditions.", indent=True)

    # ======================= CHAPTER 7 =======================
    R.chapter_heading(CHAPTERS[6])
    R.section("Tumour Measurement from the Segmentation Mask")
    R.para("The predicted mask is binarised at a user-adjustable threshold (default 0.5). With the in-plane pixel spacing Δx, Δy taken from the DICOM header "
           "(or a user-supplied value for JPEG/PNG input), the system computes the tumour area, the longest diameter d~1~ (from principal-component analysis of the "
           "mask coordinates) and the longest perpendicular diameter d~2~:", indent=True)
    R.equation(EQ["area"])
    R.para("Because the input is a single 2D slice, the system reports **area and diameters, not 3D volume**; volume would require the full MRI series.", indent=True)
    R.section("Follow-Up Comparison (RANO-Inspired)")
    R.para("The Response Assessment in Neuro-Oncology (RANO) criteria [20] assess response using the product of perpendicular diameters of enhancing lesions. Given a "
           "baseline scan (P~0~) and a follow-up scan (P~1~) of the same patient, the module computes", indent=True)
    R.equation(EQ["rano"])
    R.para(f"and maps the change to a response category (Figure {R.fig_n + 1}, Table {R.tab_n + 1}). A colour difference map shows regions that disappeared (green), appeared (red) and remained (yellow).", indent=True)
    R.figure(FIG("fig_rano.png"), "Imaging-based follow-up decision logic.", 15.5)
    R.table("RANO-inspired response categories used by the follow-up module", ["Category", "Imaging rule (2D product)", "Suggested action (for discussion)"],
            [["Complete response (CR)", "Lesion no longer visible", "Continue surveillance"], ["Partial response (PR)", "Decrease of 50% or more", "Continue current therapy"],
             ["Stable disease (SD)", "Between −50% and +25%", "Regular follow-up imaging"], ["Progressive disease (PD)", "Increase of 25% or more, or new lesion", "Refer for clinical review"]],
            [4.6, 5.4, 6.0], align=["left", "left", "left"])
    R.para("Clinical RANO also considers non-enhancing disease, steroid dose and neurological status, and requires scans to be aligned. Our module was functionally "
           "tested with controlled pairs created by shrinking and enlarging real ground-truth masks; validation on real longitudinal cohorts is future work.", indent=True)
    R.section("Software Architecture and Technology Stack")
    R.table("Technology stack", ["Layer", "Tools"],
            [["Data and ML", "Python 3, NumPy, OpenCV, scikit-image, scikit-learn"], ["Deep learning", "PyTorch, torchvision, timm (EfficientNet-B0)"],
             ["Backend API", "FastAPI, Uvicorn, Pydantic"], ["Frontend", "HTML5, Tailwind CSS, vanilla JavaScript (light theme)"],
             ["Reports", "ReportLab (PDF)"], ["Testing / deployment", "pytest, Docker, docker-compose"]], [4.0, 12.0], align=["left", "left"])
    R.section("REST API Endpoints")
    R.table("Main REST endpoints of the web application", ["Endpoint", "Method", "Input → Output"],
            [["/api/health", "GET", "→ service status, loaded models, device"], ["/api/predict", "POST", "MRI slice + model choice → class probabilities, Grad-CAM/Grad-CAM++ overlays, mask, measurements"],
             ["/api/longitudinal", "POST", "Baseline + follow-up slices, pixel spacing, interval → Δarea, %ΔP, category, difference map"],
             ["/api/report", "POST", "Patient details + latest result → downloadable PDF report"], ["/api/metrics", "GET", "→ stored evaluation metrics of all trained models"]],
            [3.4, 1.8, 10.8], align=["left", "center", "left"])
    R.section("Web Application")
    R.para(f"The single-page interface has tabs for single-scan analysis, follow-up comparison, report generation and model metrics. For a single scan the user "
           "uploads an image (or picks a sample from the public test set), selects the classifier, and sees the probability bars, Grad-CAM/Grad-CAM++ overlays with "
           "an opacity slider, the segmentation mask and the measurements. Figure {R.fig_n + 1} shows the visual output produced by the trained EfficientNet-B0 for one test image.", indent=True)
    R.figure(FIG("fig_inference.png"), "Example output of the analysis pipeline for an unseen test image (EfficientNet-B0).", 16.0)
    if os.path.exists(FIG("fig_webapp.png")):
        R.figure(FIG("fig_webapp.png"), "Interactive web application interface showing model selection, delineation overlay, Grad-CAM interpretability, and 2D planar measurements.", 16.0)
    R.section("PDF Report, Testing and Deployment")
    R.para(f"The report generator assembles patient details, the predicted class with probabilities, overlay images, measurements and a disclaimer into a PDF. "
           f"Automated pytest tests check preprocessing, model output shapes, Grad-CAM, metric calculations, follow-up categories and all API endpoints. The application "
           f"is packaged with Docker. In the reference run, EfficientNet-B0 inference took about {E['cpu_infer_ms_per_img']:.0f} ms per image on a 2-core CPU.", indent=True)

    # ======================= CHAPTER 8 =======================
    R.chapter_heading(CHAPTERS[7])
    R.section("Advantages")
    R.bullets(["Uses a public dataset and a reproducible, leakage-free evaluation protocol; all numbers can be regenerated from the provided scripts.",
               "Compares classical ML and deep learning side by side, showing the benefit of each design choice.",
               "Every prediction is accompanied by Grad-CAM and Grad-CAM++ heatmaps for visual verification.",
               "Combines classification, segmentation, measurement and follow-up comparison in one web application with PDF reports.",
               "Lightweight models (about 1–4 million parameters) run on an ordinary laptop CPU."])
    R.section("Limitations")
    R.bullets(["The classification dataset is a mix of public sources with unknown patient identities; a patient-level split is not possible for it.",
               "The system analyses single 2D slices; it does not use the full 3D MRI volume or multiple sequences together.",
               "Glioma sub-types and WHO grades are not distinguished.",
               "The follow-up module is imaging-only, assumes comparable slices and has not been validated on real longitudinal cohorts.",
               "The system has not been evaluated prospectively or by radiologists and is not a medical device."])
    R.section("Future Scope")
    R.bullets(["Train 3D models on multi-sequence datasets such as BraTS [21] to obtain true tumour volumes.",
               "Evaluate on an external dataset from a different hospital to measure generalisation.",
               "Add calibrated uncertainty estimates and test-time augmentation.",
               "Register baseline and follow-up scans automatically before comparison.",
               "Conduct a reader study with radiologists to assess whether the tool saves time."])

    # ======================= CHAPTER 9 =======================
    R.chapter_heading(CHAPTERS[8])
    R.para("This project developed a complete, reproducible pipeline for brain-tumour detection and monitoring from MRI using machine learning and convolutional "
           "neural networks on public data. A data-quality audit revealed that most of the official test images of a popular dataset are near-duplicates of training "
           "images; building a de-duplicated split was therefore an essential first step.", indent=True)
    R.para(f"On this leakage-free split, the HOG + SVM baseline achieved {pc(C['SVM (RBF)']['accuracy'])} accuracy, a custom CNN {pc(Cn['accuracy'])}, its "
           f"Squeeze-and-Excitation variant {pc(Sn['accuracy'])}, and a fine-tuned EfficientNet-B0 {pc(E['accuracy'])} with a macro ROC-AUC of {E['roc_auc_ovr_macro']:.3f}. "
           "Grad-CAM and Grad-CAM++ showed which region each prediction relied on and helped to explain errors, several of which point to label noise in the public data. Segmentation with U-Net and "
           "Attention U-Net enables tumour measurement and a RANO-inspired follow-up comparison, all accessible through a web application with PDF reporting.", indent=True)
    R.para("The main lessons are that careful data preparation matters as much as model choice, that transfer learning is the most effective approach for small "
           "medical datasets, and that explanations should accompany every automated prediction. The system is a sound academic foundation for further "
           "validation on 3D, multi-centre data.", indent=True)

    # ======================= REFERENCES =======================
    R.front_heading("REFERENCES")
    refs = [
        "F. Bray et al., “Global cancer statistics 2022: GLOBOCAN estimates of incidence and mortality worldwide for 36 cancers in 185 countries,” CA: A Cancer Journal for Clinicians, vol. 74, no. 3, pp. 229–263, 2024.",
        "D. N. Louis et al., “The 2021 WHO Classification of Tumors of the Central Nervous System: a summary,” Neuro-Oncology, vol. 23, no. 8, pp. 1231–1251, 2021.",
        "N. Dalal and B. Triggs, “Histograms of oriented gradients for human detection,” in Proc. IEEE CVPR, 2005, pp. 886–893.",
        "C. Cortes and V. Vapnik, “Support-vector networks,” Machine Learning, vol. 20, no. 3, pp. 273–297, 1995.",
        "L. Breiman, “Random forests,” Machine Learning, vol. 45, no. 1, pp. 5–32, 2001.",
        "D. P. Kingma and J. Ba, “Adam: A method for stochastic optimization,” in Proc. ICLR, 2015.",
        "M. Tan and Q. V. Le, “EfficientNet: Rethinking model scaling for convolutional neural networks,” in Proc. ICML, 2019, pp. 6105–6114.",
        "J. Hu, L. Shen, and G. Sun, “Squeeze-and-Excitation networks,” in Proc. IEEE CVPR, 2018, pp. 7132–7141.",
        "O. Ronneberger, P. Fischer, and T. Brox, “U-Net: Convolutional networks for biomedical image segmentation,” in Proc. MICCAI, 2015, pp. 234–241.",
        "O. Oktay et al., “Attention U-Net: Learning where to look for the pancreas,” in Proc. MIDL, 2018.",
        "R. R. Selvaraju et al., “Grad-CAM: Visual explanations from deep networks via gradient-based localization,” in Proc. IEEE ICCV, 2017, pp. 618–626.",
        "A. Chattopadhyay, A. Sarkar, P. Howlader, and V. N. Balasubramanian, “Grad-CAM++: Generalized gradient-based visual explanations for deep convolutional networks,” in Proc. IEEE WACV, 2018, pp. 839–847.",
        "J. Cheng, “Brain tumor dataset,” Figshare, 2017, doi: 10.6084/m9.figshare.1512427.v5.",
        "J. Cheng et al., “Enhanced performance of brain tumor classification via tumor region augmentation and partition,” PLoS ONE, vol. 10, no. 10, e0140381, 2015.",
        "P. Afshar, A. Mohammadi, and K. N. Plataniotis, “Brain tumor type classification via capsule networks,” in Proc. IEEE ICIP, 2018, pp. 3129–3133.",
        "S. Deepak and P. M. Ameer, “Brain tumor classification using deep CNN features via transfer learning,” Computers in Biology and Medicine, vol. 111, 103345, 2019.",
        "Z. N. K. Swati et al., “Brain tumor classification for MR images using transfer learning and fine-tuning,” Computerized Medical Imaging and Graphics, vol. 75, pp. 34–46, 2019.",
        "M. M. Badža and M. Č. Barjaktarović, “Classification of brain tumors from MRI images using a convolutional neural network,” Applied Sciences, vol. 10, no. 6, 1999, 2020.",
        "S. Bhuvaji, A. Kadam, P. Bhumkar, S. Dedge, and S. Kanchan, “Brain Tumor Classification (MRI),” Kaggle dataset, 2020, doi: 10.34740/KAGGLE/DSV/1183165.",
        "P. Y. Wen et al., “Updated response assessment criteria for high-grade gliomas: Response Assessment in Neuro-Oncology Working Group,” Journal of Clinical Oncology, vol. 28, no. 11, pp. 1963–1972, 2010.",
        "B. H. Menze et al., “The multimodal brain tumor image segmentation benchmark (BRATS),” IEEE Transactions on Medical Imaging, vol. 34, no. 10, pp. 1993–2024, 2015.",
        "I. Loshchilov and F. Hutter, “Decoupled weight decay regularization,” in Proc. ICLR, 2019.",
        "L. N. Smith and N. Topin, “Super-convergence: Very fast training of neural networks using large learning rates,” in Proc. SPIE Artificial Intelligence and Machine Learning for Multi-Domain Operations Applications, 2019.",
        "K. Zuiderveld, “Contrast limited adaptive histogram equalization,” in Graphics Gems IV, Academic Press, 1994, pp. 474–485.",
    ]
    for i, r in enumerate(refs, 1):
        p = R.d.add_paragraph(); pf = p.paragraph_format; pf.left_indent = Cm(1.0); pf.first_line_indent = Cm(-1.0); pf.space_after = Pt(4); pf.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; R.runs(p, f"[{i}]\t{r}", size=11)
        pf.tab_stops.add_tab_stop(Cm(1.0))
    return R


CHAPTERS = ["Introduction", "Background and Literature Review", "Dataset and Data Preparation", "Methodology and Model Architectures",
            "Explainable AI", "Experimental Results and Evaluation", "Tumour Measurement, Monitoring and Implementation",
            "Advantages, Limitations and Future Scope", "Conclusion"]


def to_pdf(docx):
    soffice = "soffice"
    if not shutil.which(soffice):
        for candidate in [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/usr/local/bin/soffice",
            "/opt/homebrew/bin/soffice",
        ]:
            if os.path.exists(candidate):
                soffice = candidate
                break
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", OUT, docx], check=True, capture_output=True, timeout=600)
    return docx[:-5] + ".pdf"


def find_pages(pdf, R):
    pages = {"_figs": R.figures, "_tabs": R.tables}
    if not os.path.exists(pdf):
        return pages
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf)
        n = len(reader.pages)
        texts = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        if shutil.which("pdfinfo") and shutil.which("pdftotext"):
            n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
            texts = [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", pdf, "-"], capture_output=True, text=True).stdout for i in range(1, n + 1)]
        else:
            return pages
    def first(pattern, start=0):
        for i in range(start, n):
            if re.search(pattern, texts[i], re.M): return i
        return None
    for k in ["CERTIFICATE", "ACKNOWLEDGEMENT", "DECLARATION", "ABSTRACT", "CONTENTS", "LIST OF FIGURES", "LIST OF TABLES"]:
        i = first(r"^\s*" + k + r"\s*$")
        if i is not None: pages[k] = i + 1
    lot = pages.get("LIST OF TABLES", 1)
    ch1 = first(r"CHAPTER 1 –", lot) or lot
    for c in range(1, len(CHAPTERS) + 1):
        i = first(rf"CHAPTER {c} –", ch1)
        if i is not None: pages[f"CH{c}"] = i + 1
    i = first(r"^\s*REFERENCES\s*$", ch1 + 1)
    if i is not None: pages["REFERENCES"] = i + 1
    for k in range(1, len(R.figures) + 1):
        i = first(rf"^\s*Figure {k}\.\s", ch1)
        if i is not None: pages[f"F{k}"] = i + 1
    for k in range(1, len(R.tables) + 1):
        i = first(rf"^\s*Table {k}\.\s", ch1)
        if i is not None: pages[f"T{k}"] = i + 1
    return pages


if __name__ == "__main__":
    name = "Final_Report_Brain_Tumor_Detection_OUTR"
    R = build({"_figs": [], "_tabs": []})
    # pass 1 with full lists (so LOF/LOT occupy their real length)
    R = build({"_figs": R.figures, "_tabs": R.tables})
    path = os.path.join(OUT, name + ".docx"); R.save(path)
    pages = find_pages(to_pdf(path), R)
    R = build(pages); R.save(path)
    pdf = to_pdf(path)
    pages2 = find_pages(pdf, R)
    diff = {k: (pages.get(k), pages2.get(k)) for k in pages2 if not k.startswith("_") and pages.get(k) != pages2.get(k)}
    if diff:
        R = build(pages2); R.save(path); pdf = to_pdf(path)
    print("built", path, pdf, "page drift fixed:" if diff else "", diff)
