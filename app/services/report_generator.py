"""Automated PDF Report Generation Module.
Produces standardized academic decision-support reports with 2D planar measurements,
model predictions, interpretability maps, and clear academic disclaimers.

Academic Reference:
Chinmayee Patra (23110206) & Shruti Sameekshya Dehury (23110234)
Supervised by Mrs. Swarna Lata Pati
Department of Computer Science and Engineering
Odisha University of Technology and Research (OUTR), Bhubaneswar
"""
import io
import datetime
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
)
from app.config import REPORTS_DIR

ACADEMIC_DISCLAIMER = "Academic decision-support prototype — not for clinical diagnosis."


class ClinicalReportGenerator:
    """Generates academic decision-support PDF reports for MRI lesion evaluation."""

    @staticmethod
    def generate_pdf_report(
        inference_result: dict,
        longitudinal_result: dict = None,
        patient_info: dict = None,
        output_filename: str = None
    ) -> str:
        """Builds an academic PDF analysis report and writes it to disk.
        Returns the absolute file path of the generated PDF.
        """
        if patient_info is None:
            patient_info = {
                "patient_id": f"SUBJ-{datetime.datetime.now().strftime('%Y%m%d')}-042",
                "patient_name": "Anonymous Subject",
                "exam_date": datetime.datetime.now().strftime("%B %d, %Y - %H:%M"),
                "modality": "Brain MRI (T1-CE / Axial Slice)",
            }

        if output_filename is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"brain_mri_report_{ts}.pdf"

        report_path = REPORTS_DIR / output_filename
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(report_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0f172a")    # Slate 900
        accent_color = colors.HexColor("#0284c7")     # Sky 600
        danger_color = colors.HexColor("#dc2626")     # Red 600
        success_color = colors.HexColor("#16a34a")    # Green 600
        warning_color = colors.HexColor("#d97706")    # Amber 600

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=primary_color,
            spaceAfter=3
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=6
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            textColor=accent_color,
            spaceBefore=6,
            spaceAfter=3
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#334155")
        )
        bold_style = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold"
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=colors.HexColor("#991b1b"),
            alignment=1
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph("Brain MRI Analysis Report (Academic Prototype)", title_style))
        elements.append(Paragraph(
            "Final Year B.Tech Project &bull; Odisha University of Technology and Research (OUTR), Bhubaneswar<br/>"
            "<b>Authors:</b> Chinmayee Patra (23110206), Shruti Sameekshya Dehury (23110234) &bull; "
            "<b>Supervisor:</b> Mrs. Swarna Lata Pati",
            subtitle_style
        ))

        # Prominent Academic Disclaimer Banner
        disc_table = Table([[Paragraph(f"<b>NOTICE:</b> {ACADEMIC_DISCLAIMER}", disclaimer_style)]], colWidths=[540])
        disc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#f87171")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(disc_table)
        elements.append(Spacer(1, 6))

        # 2. Patient & Examination Information Table
        pred = inference_result.get("prediction", {})
        seg = inference_result.get("segmentation", {})
        qm = inference_result.get("quantitative_metrics", {})

        meta_data = [
            [
                Paragraph(f"<b>Subject ID:</b> {patient_info.get('patient_id')}", body_style),
                Paragraph(f"<b>Evaluation Date:</b> {patient_info.get('exam_date')}", body_style)
            ],
            [
                Paragraph(f"<b>Modality:</b> {patient_info.get('modality')}", body_style),
                Paragraph(f"<b>Classifier Model:</b> {pred.get('model_name', 'EfficientNet-B0')}", body_style)
            ],
            [
                Paragraph(f"<b>Segmentation Architecture:</b> {seg.get('architecture_used', 'Attention U-Net')}", body_style),
                Paragraph(f"<b>Pixel Spacing:</b> {qm.get('spacing_source', 'not provided')}", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 6))

        # 3. Model Classification Finding Box
        is_tumor = pred.get("is_tumor_detected", False)
        box_bg = colors.HexColor("#fef2f2") if is_tumor else colors.HexColor("#f0fdf4")
        box_border = danger_color if is_tumor else success_color
        status_text = "Focal Intracranial Mass Detected" if is_tumor else "No Mass / Normal Brain Parenchyma"

        dist_str = " | ".join([f"{k}: {v}%" for k, v in pred.get("distribution", {}).items()])
        finding_p = Paragraph(
            f"<b>MODEL PREDICTION:</b> <font color='{box_border.hexval()}'><b>{pred.get('label', 'Unknown').upper()}</b></font> &nbsp;|&nbsp; "
            f"<b>{status_text}</b> &nbsp;|&nbsp; Confidence: <b>{pred.get('confidence_percent', 0.0):.1f}%</b><br/>"
            f"<font size=7.5 color='#475569'>Class Probabilities: {dist_str}</font>",
            body_style
        )
        finding_table = Table([[finding_p]], colWidths=[540])
        finding_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), box_bg),
            ('BOX', (0, 0), (-1, -1), 1.0, box_border),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(finding_table)
        elements.append(Spacer(1, 6))

        # 4. Visual Triad (Original MRI | Segmentation Overlay | Grad-CAM Saliency)
        elements.append(Paragraph("IMAGE VISUALIZATION & INTERPRETABILITY PANEL", section_style))
        vis = inference_result.get("visualizations", {})
        from app.services.preprocessor import MedicalImagePreprocessor

        img_cells = []
        lbl_cells = []
        panels = [
            ("original_base64", "1. Input MRI Slice"),
            ("segmentation_overlay_base64", "2. Lesion Delineation"),
            ("gradcam_base64", "3. Grad-CAM Activation")
        ]
        for key, title in panels:
            b64 = vis.get(key)
            if b64:
                pil_img = MedicalImagePreprocessor.base64_to_pil(b64)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                buf.seek(0)
                rl_img = RLImage(buf, width=155, height=155)
                img_cells.append(rl_img)
                lbl_cells.append(Paragraph(f"<para align=center><b>{title}</b></para>", body_style))

        if img_cells:
            image_table = Table([img_cells, lbl_cells], colWidths=[180, 180, 180])
            image_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(image_table)
        elements.append(Spacer(1, 6))

        # 5. Quantitative 2D Morphometrics Table
        elements.append(Paragraph("QUANTITATIVE 2D PLANAR MEASUREMENTS (INDEX SLICE)", section_style))
        has_spacing = qm.get("area_mm2") is not None and qm.get("area_mm2", 0) > 0

        if has_spacing:
            area_str = f"{qm.get('area_mm2', 0.0):.1f} mm² ({qm.get('area_cm2', 0.0):.2f} cm²)"
            d1_str = f"{qm.get('d1_mm', 0.0):.1f} mm"
            d2_str = f"{qm.get('d2_mm', 0.0):.1f} mm"
            prod_str = f"{qm.get('product_mm2', 0.0):.1f} mm²"
        else:
            area_str = f"{qm.get('pixel_count', 0)} pixels (uncalibrated)"
            d1_str = f"{qm.get('d1_px', 0.0):.1f} px"
            d2_str = f"{qm.get('d2_px', 0.0):.1f} px"
            prod_str = f"{qm.get('product_px2', 0.0):.1f} px²"

        quant_data = [
            [Paragraph("<b>Parameter</b>", bold_style), Paragraph("<b>Measurement</b>", bold_style), Paragraph("<b>Method / Definition</b>", bold_style)],
            [Paragraph("2D Lesion Area", body_style), Paragraph(f"<b>{area_str}</b>", body_style), Paragraph("Planar cross-sectional area: N_pixels &times; &Delta;x &times; &Delta;y", body_style)],
            [Paragraph("Longest Diameter (d1)", body_style), Paragraph(f"<b>{d1_str}</b>", body_style), Paragraph("PCA major-axis planar span of delineated lesion", body_style)],
            [Paragraph("Perpendicular Diameter (d2)", body_style), Paragraph(f"<b>{d2_str}</b>", body_style), Paragraph("Max perpendicular span along orthogonal PCA axis", body_style)],
            [Paragraph("Perpendicular Product (d1 &times; d2)", body_style), Paragraph(f"<b>{prod_str}</b>", body_style), Paragraph("Bi-dimensional product (RANO 2D planar criterion)", body_style)],
            [Paragraph("Mask Pixel Count", body_style), Paragraph(f"{qm.get('pixel_count', 0):,} pixels", body_style), Paragraph("Total segmented positive pixels at threshold 0.5", body_style)],
        ]
        quant_table = Table(quant_data, colWidths=[150, 160, 230])
        quant_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(quant_table)
        elements.append(Spacer(1, 6))

        # 6. Longitudinal Assessment (if provided)
        if longitudinal_result:
            elements.append(Paragraph("LONGITUDINAL COMPARISON & RANO RESPONSE ASSESSMENT", section_style))
            rc = longitudinal_result.get("response_category", "SD")
            p_change = longitudinal_result.get("percent_change_product", 0.0)
            note = longitudinal_result.get("note", "")

            rc_color = danger_color if rc == "PD" else (success_color if rc in ["PR", "CR"] else warning_color)
            long_data = [
                [Paragraph("<b>Comparison Metric</b>", bold_style), Paragraph("<b>Value</b>", bold_style)],
                [Paragraph("Baseline Product (P0)", body_style), Paragraph(f"{longitudinal_result.get('baseline_product_mm2', 0.0):.1f} mm²", body_style)],
                [Paragraph("Follow-up Product (P1)", body_style), Paragraph(f"{longitudinal_result.get('followup_product_mm2', 0.0):.1f} mm²", body_style)],
                [Paragraph("Bi-dimensional Change (%&Delta;P)", body_style), Paragraph(f"<b>{p_change:+.1f}%</b>", body_style)],
                [Paragraph("Response Category", body_style), Paragraph(f"<font color='{rc_color.hexval()}'><b>{rc}</b></font> ({longitudinal_result.get('response_summary', '')})", body_style)],
                [Paragraph("Clinical Caveat", body_style), Paragraph(f"<font size=7.5 color='#64748b'>{note}</font>", body_style)]
            ]
            long_table = Table(long_data, colWidths=[170, 370])
            long_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(long_table)
            elements.append(Spacer(1, 6))

        # 7. Academic Summary & Verification
        elements.append(Paragraph("TECHNICAL VERIFICATION & SUMMARY", section_style))
        summary_text = (
            f"The image was analyzed using an automated machine learning pipeline consisting of "
            f"<b>{pred.get('model_name', 'EfficientNet-B0')}</b> for 4-class classification and "
            f"<b>{seg.get('architecture_used', 'Attention U-Net')}</b> for lesion delineation. "
            f"Grad-CAM salience mapping was used to assess feature attribution against the segmented region. "
            f"All models were trained and evaluated on publicly available research benchmarks "
            f"(Sartaj Bhuvaji et al. 2020; Figshare Cheng et al.). "
            f"This software is developed strictly as an academic engineering prototype. "
            f"It is not approved by medical regulatory authorities and must not be used for clinical diagnosis or treatment guidance."
        )
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 10))

        # Project Authors Footer Table
        author_data = [
            [
                Paragraph("<b>Project Supervisor:</b><br/>Mrs. Swarna Lata Pati<br/><font size=7 color='#64748b'>Dept. of CSE, OUTR Bhubaneswar</font>", body_style),
                Paragraph("<b>Student Investigators:</b><br/>Chinmayee Patra (23110206)<br/>Shruti Sameekshya Dehury (23110234)", body_style),
                Paragraph("<b>Institutional Affiliation:</b><br/>Odisha University of Technology and Research<br/><font size=7 color='#64748b'>Bhubaneswar, Odisha, India</font>", body_style)
            ]
        ]
        author_table = Table(author_data, colWidths=[180, 180, 180])
        author_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(author_table)

        doc.build(elements)
        return str(report_path)
