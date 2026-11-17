// Brain MRI Analysis & Longitudinal Monitoring Controller (Academic Prototype)

let currentInferenceData = null;
let currentViewMode = 'segmentation'; // 'original' | 'segmentation' | 'gradcam' | 'gradcam_pp' | 'attention_gate' | 'mask_only'
let currentClassifier = 'effb0';
let currentSegArch = 'attunet';
let currentPixelSpacing = null;
let currentGradcamAlpha = 0.45;
let currentMaskThresh = 0.50;
let currentSampleKey = 'glioma';
let currentUploadedFile = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  fetchHealthAndDevice();
  loadSample('glioma');
});

// Device and Health Check
async function fetchHealthAndDevice() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById('deviceBadge');
      if (badge && data.device) {
        badge.textContent = `DEVICE: ${data.device.toUpperCase()}`;
      }
    }
  } catch (err) {
    console.error('Failed to query health endpoint:', err);
  }
}

// Tab Navigation
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);

  if (targetTab) targetTab.classList.remove('hidden');
  if (targetBtn) targetBtn.classList.add('active');

  lucide.createIcons();

  if (tabId === 'longitudinal') {
    runLongitudinalAnalysis();
  } else if (tabId === 'evaluation') {
    loadModelEvaluationMetrics();
  }
}

// Layer Mode Switching (MRI, Delineation, Grad-CAM, Grad-CAM++, Attention Gate, Binary Mask)
function setViewMode(mode) {
  currentViewMode = mode;

  const buttons = {
    'original': 'btn-mode-orig',
    'segmentation': 'btn-mode-seg',
    'gradcam': 'btn-mode-cam',
    'gradcam_pp': 'btn-mode-cam-pp',
    'attention_gate': 'btn-mode-ag',
    'mask_only': 'btn-mode-mask'
  };

  Object.entries(buttons).forEach(([m, id]) => {
    const btn = document.getElementById(id);
    if (btn) {
      if (m === mode) {
        btn.className = 'px-2.5 py-1 rounded text-xs font-semibold bg-blue-600 text-white shadow-sm transition';
      } else {
        btn.className = 'px-2.5 py-1 rounded text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition';
      }
    }
  });

  updateViewerDisplay();
}

// Update Viewport Display
function updateViewerDisplay() {
  if (!currentInferenceData || !currentInferenceData.visualizations) return;
  const imgEl = document.getElementById('viewerImage');
  const hudEl = document.getElementById('hudCoordinates');
  const vis = currentInferenceData.visualizations;

  if (currentViewMode === 'original') {
    imgEl.src = vis.original_base64;
    if (hudEl) hudEl.textContent = 'Axial T1-CE Original MRI';
  } else if (currentViewMode === 'segmentation') {
    imgEl.src = vis.segmentation_overlay_base64;
    if (hudEl) hudEl.textContent = currentSegArch === 'attunet' ? 'Attention U-Net Overlay' : 'U-Net Overlay';
  } else if (currentViewMode === 'gradcam') {
    imgEl.src = vis.gradcam_base64;
    if (hudEl) hudEl.textContent = 'Grad-CAM Saliency';
  } else if (currentViewMode === 'gradcam_pp') {
    imgEl.src = vis.gradcam_pp_base64;
    if (hudEl) hudEl.textContent = 'Grad-CAM++ Saliency';
  } else if (currentViewMode === 'attention_gate') {
    imgEl.src = vis.attention_gate_base64;
    if (hudEl) hudEl.textContent = 'Attention Gate Activation';
  } else if (currentViewMode === 'mask_only') {
    imgEl.src = vis.mask_base64;
    if (hudEl) hudEl.textContent = 'Binary Predicted Mask';
  }
}

// Sample Preset Loader
async function loadSample(sampleKey) {
  currentSampleKey = sampleKey;
  currentUploadedFile = null;

  const formData = new FormData();
  formData.append('sample_key', sampleKey);
  formData.append('classifier', currentClassifier);
  formData.append('seg_architecture', currentSegArch);
  formData.append('mask_threshold', currentMaskThresh);
  formData.append('gradcam_alpha', currentGradcamAlpha);
  if (currentPixelSpacing) {
    formData.append('pixel_spacing_mm', currentPixelSpacing);
  }

  await executeInference(formData);
}

// Handle Custom File Upload
async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  currentUploadedFile = file;
  currentSampleKey = null;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('classifier', currentClassifier);
  formData.append('seg_architecture', currentSegArch);
  formData.append('mask_threshold', currentMaskThresh);
  formData.append('gradcam_alpha', currentGradcamAlpha);
  if (currentPixelSpacing) {
    formData.append('pixel_spacing_mm', currentPixelSpacing);
  }

  await executeInference(formData);
}

// Selectors
function changeClassifier(cls) {
  currentClassifier = cls;
  reRunInferenceWithParams();
}

function changeSegArchitecture(arch) {
  currentSegArch = arch;
  reRunInferenceWithParams();
}

function updatePixelSpacing(val) {
  const parsed = parseFloat(val);
  currentPixelSpacing = (!isNaN(parsed) && parsed > 0) ? parsed : null;
  reRunInferenceWithParams();
}

function updateThreshold(val) {
  currentMaskThresh = parseFloat(val);
  const el = document.getElementById('valThresh');
  if (el) el.textContent = currentMaskThresh.toFixed(2);
  reRunInferenceWithParams();
}

// Execute Inference API call
async function executeInference(formData) {
  const loading = document.getElementById('loadingOverlay');
  if (loading) loading.classList.remove('hidden');

  try {
    const response = await fetch('/api/predict', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Inference error');
    }

    currentInferenceData = await response.json();
    renderDiagnosticResults(currentInferenceData);
    updateViewerDisplay();
  } catch (error) {
    alert(`Inference failed: ${error.message}`);
  } finally {
    if (loading) loading.classList.add('hidden');
  }
}

// Render Results & 2D Planar Measurements
function renderDiagnosticResults(data) {
  const pred = data.prediction;
  const qm = data.quantitative_metrics;

  // Label, confidence & description
  const labelEl = document.getElementById('predictedLabel');
  const confEl = document.getElementById('confidenceScore');
  const descEl = document.getElementById('diagnosisDescription');
  const badgeEl = document.getElementById('tumorStatusBadge');

  if (labelEl) labelEl.textContent = pred.label;
  if (confEl) confEl.textContent = `${pred.confidence_percent.toFixed(1)}% Confidence (${pred.model_name})`;
  if (descEl) descEl.textContent = pred.clinical_description;

  if (badgeEl) {
    if (pred.is_tumor_detected) {
      badgeEl.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-red-50 text-red-700 border border-red-200';
      badgeEl.textContent = 'LESION DETECTED';
    } else {
      badgeEl.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200';
      badgeEl.textContent = 'NO TUMOR DETECTED';
    }
  }

  // Softmax Probabilities Bars
  const probsContainer = document.getElementById('classProbabilities');
  if (probsContainer && pred.distribution) {
    probsContainer.innerHTML = '';
    Object.entries(pred.distribution).forEach(([cls, prob]) => {
      const isSelected = (cls === pred.label);
      const barColor = isSelected ? 'bg-blue-600' : 'bg-slate-300';
      const textColor = isSelected ? 'text-slate-900 font-semibold' : 'text-slate-600';
      const row = document.createElement('div');
      row.className = 'space-y-1';
      row.innerHTML = `
        <div class="flex justify-between text-xs ${textColor}">
          <span>${cls}</span>
          <span class="font-mono font-medium">${prob.toFixed(1)}%</span>
        </div>
        <div class="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
          <div class="${barColor} h-2 rounded-full transition-all duration-300" style="width: ${prob}%"></div>
        </div>
      `;
      probsContainer.appendChild(row);
    });
  }

  // 2D Planar Measurements (Strictly 2D, NO volume / sphericity)
  const hasSpacing = qm.area_mm2 !== null && qm.area_mm2 > 0;
  const srcEl = document.getElementById('metricSpacingSource');
  if (srcEl) {
    srcEl.textContent = qm.spacing_source || 'Uncalibrated (pixels)';
  }

  const areaEl = document.getElementById('metricArea');
  const areaCmEl = document.getElementById('metricAreaCm');
  const d1El = document.getElementById('metricD1');
  const d2El = document.getElementById('metricD2');
  const prodEl = document.getElementById('metricProduct');

  if (hasSpacing) {
    if (areaEl) areaEl.textContent = `${qm.area_mm2.toFixed(1)} mm²`;
    if (areaCmEl) areaCmEl.textContent = `${qm.area_cm2.toFixed(2)} cm² (${qm.pixel_count.toLocaleString()} px)`;
    if (d1El) d1El.textContent = `${qm.d1_mm.toFixed(1)} mm`;
    if (d2El) d2El.textContent = `${qm.d2_mm.toFixed(1)} mm`;
    if (prodEl) prodEl.textContent = `${qm.product_mm2.toFixed(1)} mm²`;
  } else {
    if (areaEl) areaEl.textContent = `${qm.pixel_count.toLocaleString()} px`;
    if (areaCmEl) areaCmEl.textContent = 'Pixel units (spacing not provided)';
    if (d1El) d1El.textContent = `${qm.d1_px.toFixed(1)} px`;
    if (d2El) d2El.textContent = `${qm.d2_px.toFixed(1)} px`;
    if (prodEl) prodEl.textContent = `${qm.product_px2.toFixed(1)} px²`;
  }
}

// Debounced parameter update
let paramTimeout = null;
function reRunInferenceWithParams() {
  clearTimeout(paramTimeout);
  paramTimeout = setTimeout(async () => {
    const formData = new FormData();
    if (currentUploadedFile) {
      formData.append('file', currentUploadedFile);
    } else {
      formData.append('sample_key', currentSampleKey || 'glioma');
    }
    formData.append('classifier', currentClassifier);
    formData.append('seg_architecture', currentSegArch);
    formData.append('mask_threshold', currentMaskThresh);
    formData.append('gradcam_alpha', currentGradcamAlpha);
    if (currentPixelSpacing) {
      formData.append('pixel_spacing_mm', currentPixelSpacing);
    }
    await executeInference(formData);
  }, 120);
}

// Longitudinal Analysis Execution
async function runLongitudinalAnalysis() {
  try {
    const formData = new FormData();
    formData.append('baseline_sample', 'longitudinal_pair');
    formData.append('followup_sample', 'longitudinal_pair');
    formData.append('classifier', currentClassifier);
    formData.append('seg_architecture', currentSegArch);
    if (currentPixelSpacing) {
      formData.append('pixel_spacing_mm', currentPixelSpacing);
    }
    formData.append('days_between', '90');

    const res = await fetch('/api/longitudinal', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Longitudinal endpoint failed');
    const data = await res.json();
    const c = data.comparison;

    const baseAreaEl = document.getElementById('longBaseArea');
    const baseProdEl = document.getElementById('longBaseProd');
    const followAreaEl = document.getElementById('longFollowArea');
    const followProdEl = document.getElementById('longFollowProd');
    const deltaProdEl = document.getElementById('longDeltaProd');

    const units = c.units || 'mm²';
    if (baseAreaEl) baseAreaEl.textContent = `${c.baseline.area_mm2 ? c.baseline.area_mm2.toFixed(1) + ' mm²' : c.baseline.pixel_count + ' px'}`;
    if (baseProdEl) baseProdEl.textContent = `${c.baseline.product.toFixed(1)} ${units}`;
    if (followAreaEl) followAreaEl.textContent = `${c.followup.area_mm2 ? c.followup.area_mm2.toFixed(1) + ' mm²' : c.followup.pixel_count + ' px'}`;
    if (followProdEl) followProdEl.textContent = `${c.followup.product.toFixed(1)} ${units}`;

    if (deltaProdEl) {
      const sign = c.percent_change_product > 0 ? '+' : '';
      deltaProdEl.textContent = `${sign}${c.percent_change_product.toFixed(1)}% (${sign}${c.delta_product.toFixed(1)} ${units})`;
    }

    if (data.delta_map_base64) {
      const deltaImg = document.getElementById('longDeltaImg');
      if (deltaImg) deltaImg.src = data.delta_map_base64;
    }

    const titleEl = document.getElementById('longVerdictTitle');
    const textEl = document.getElementById('longVerdictText');
    const noteEl = document.getElementById('longVerdictNote');
    const badgeEl = document.getElementById('longDeltaBadge');

    if (titleEl) titleEl.textContent = `RANO Assessment: ${c.response_name}`;
    if (textEl) textEl.textContent = c.response_summary;
    if (noteEl) noteEl.textContent = c.neutral_note || 'Imaging change only.';
    if (badgeEl) badgeEl.textContent = c.response_name;

    const box = document.getElementById('longitudinalVerdictBox');
    if (box) {
      if (c.category === 'PR' || c.category === 'CR') {
        box.className = 'p-4 rounded-lg bg-blue-50 border border-blue-200 flex items-start space-x-3';
      } else if (c.category === 'PD') {
        box.className = 'p-4 rounded-lg bg-red-50 border border-red-200 flex items-start space-x-3';
      } else {
        box.className = 'p-4 rounded-lg bg-amber-50 border border-amber-200 flex items-start space-x-3';
      }
    }

    lucide.createIcons();
  } catch (err) {
    console.error('Longitudinal error:', err);
  }
}

// Load Real Model Evaluation Metrics from /api/metrics
async function loadModelEvaluationMetrics() {
  const tbody = document.getElementById('evaluationTableBody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/metrics');
    if (!res.ok) throw new Error('Could not load metrics');
    const data = await res.json();

    const m = data.models || {};
    const seg = data.segmentation || {};
    const leak = data.leakage || {};

    const rows = [
      {
        name: 'HOG + SVM',
        split: 'Clean 70/15/15',
        params: 'N/A (sklearn)',
        acc: m.svm ? (m.svm.accuracy * 100).toFixed(2) : '--',
        f1: m.svm ? (m.svm.macro_f1 * 100).toFixed(2) : '--',
        auc: m.svm ? m.svm.roc_auc.toFixed(4) : '--',
        dice: 'N/A (Classifier)',
        highlight: false,
      },
      {
        name: 'Custom CNN',
        split: 'Clean 70/15/15',
        params: m.cnn ? m.cnn.n_params.toLocaleString() : '1,206,052',
        acc: m.cnn ? (m.cnn.accuracy * 100).toFixed(2) : '--',
        f1: m.cnn ? (m.cnn.macro_f1 * 100).toFixed(2) : '--',
        auc: m.cnn ? m.cnn.roc_auc.toFixed(4) : '--',
        dice: 'N/A (Classifier)',
        highlight: false,
      },
      {
        name: 'SE-CNN',
        split: 'Clean 70/15/15',
        params: m.secnn ? m.secnn.n_params.toLocaleString() : '1,228,352',
        acc: m.secnn ? (m.secnn.accuracy * 100).toFixed(2) : '--',
        f1: m.secnn ? (m.secnn.macro_f1 * 100).toFixed(2) : '--',
        auc: m.secnn ? m.secnn.roc_auc.toFixed(4) : '--',
        dice: 'N/A (Classifier)',
        highlight: false,
      },
      {
        name: 'EfficientNet-B0 (transfer learning)',
        split: 'Clean 70/15/15',
        params: m.effb0 ? m.effb0.n_params.toLocaleString() : '4,012,672',
        acc: m.effb0 ? (m.effb0.accuracy * 100).toFixed(2) : '--',
        f1: m.effb0 ? (m.effb0.macro_f1 * 100).toFixed(2) : '--',
        auc: m.effb0 ? m.effb0.roc_auc.toFixed(4) : '--',
        dice: 'N/A (Classifier)',
        highlight: true,
      },
      {
        name: 'EfficientNet-B0 (official split)',
        split: 'Official Sartaj (Leakage)',
        params: m.effb0_official ? m.effb0_official.n_params.toLocaleString() : '4,012,672',
        acc: m.effb0_official ? (m.effb0_official.accuracy * 100).toFixed(2) : '--',
        f1: m.effb0_official ? (m.effb0_official.macro_f1 * 100).toFixed(2) : '--',
        auc: m.effb0_official ? m.effb0_official.roc_auc.toFixed(4) : '--',
        dice: 'N/A (Leakage test)',
        highlight: false,
      },
      {
        name: 'U-Net',
        split: 'Figshare Patient-Level (35 PIDs)',
        params: seg.unet_params ? seg.unet_params.toLocaleString() : '7,762,465',
        acc: '--',
        f1: '--',
        auc: '--',
        dice: seg.unet_dice ? `${(seg.unet_dice * 100).toFixed(1)}% / ${(seg.unet_iou * 100).toFixed(1)}%` : '--',
        highlight: false,
      },
      {
        name: 'Attention U-Net',
        split: 'Figshare Patient-Level (35 PIDs)',
        params: seg.attunet_params ? seg.attunet_params.toLocaleString() : '8,105,201',
        acc: '--',
        f1: '--',
        auc: '--',
        dice: seg.attunet_dice ? `${(seg.attunet_dice * 100).toFixed(1)}% / ${(seg.attunet_iou * 100).toFixed(1)}%` : '--',
        highlight: true,
      },
    ];

    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      if (r.highlight) {
        tr.className = 'bg-blue-50/70 text-blue-950 font-semibold';
      }
      tr.innerHTML = `
        <td class="p-2.5 font-sans">${r.name}</td>
        <td class="p-2.5 text-slate-500 font-sans">${r.split}</td>
        <td class="p-2.5 text-right">${r.params}</td>
        <td class="p-2.5 text-right ${r.highlight ? 'text-blue-700 font-bold' : ''}">${r.acc}</td>
        <td class="p-2.5 text-right">${r.f1}</td>
        <td class="p-2.5 text-right">${r.auc}</td>
        <td class="p-2.5 text-right ${r.highlight ? 'text-emerald-700 font-bold' : ''}">${r.dice}</td>
      `;
      tbody.appendChild(tr);
    });

    if (leak.n_leak_pairs !== undefined) {
      const lp = document.getElementById('leakagePairs');
      if (lp) lp.textContent = `${leak.n_leak_pairs} pairs`;
    }

    if (seg.n_test_images && seg.n_test_patients) {
      const st = document.getElementById('segTestInfo');
      if (st) st.textContent = `${seg.n_test_images} slices (${seg.n_test_patients} patients)`;
    }
  } catch (err) {
    console.error('Failed to load metrics:', err);
    tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-red-500 font-sans">Error loading metrics: ${err.message}</td></tr>`;
  }
}

// PDF Generation & Download
async function handleReportGenerate(e) {
  e.preventDefault();
  const btn = document.getElementById('btnGenerateReport');
  btn.disabled = true;
  btn.innerHTML = `<span>Generating Academic PDF Report...</span>`;

  try {
    const formData = new FormData();
    formData.append('patient_name', document.getElementById('repPatientName').value);
    formData.append('patient_id', document.getElementById('repPatientId').value);
    formData.append('classifier', document.getElementById('repClassifier').value);
    formData.append('seg_architecture', currentSegArch);
    formData.append('sample_key', document.getElementById('repSampleKey').value);
    if (currentPixelSpacing) {
      formData.append('pixel_spacing_mm', currentPixelSpacing);
    }
    formData.append('include_longitudinal', document.getElementById('repIncludeLong').checked);

    const res = await fetch('/api/report', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Report generation failed');
    const data = await res.json();

    const successBox = document.getElementById('reportSuccessBox');
    const dlLink = document.getElementById('reportDownloadLink');
    if (successBox) successBox.classList.remove('hidden');
    if (dlLink) dlLink.href = data.download_url;

    // Trigger download in new tab
    window.open(data.download_url, '_blank');
  } catch (err) {
    alert(`Could not generate report: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="download" class="w-4 h-4"></i><span>Generate & Download Academic PDF Report</span>`;
    lucide.createIcons();
  }
}

function triggerPdfExport() {
  switchTab('report');
}
