// Clinical AI PACS Workstation Controller

let currentInferenceData = null;
let currentViewMode = 'segmentation'; // 'original' | 'segmentation' | 'gradcam' | 'mask_only'
let currentGradcamAlpha = 0.45;
let currentMaskThresh = 0.50;
let currentSampleKey = 'glioma';
let currentUploadedFile = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  // Automatically run initial inference on Glioma sample
  loadSample('glioma');
});

// Tab Navigation
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active', 'text-white'));
  
  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);
  
  if (targetTab) targetTab.classList.remove('hidden');
  if (targetBtn) targetBtn.classList.add('active', 'text-white');
  
  lucide.createIcons();

  if (tabId === 'longitudinal') {
    runLongitudinalAnalysis();
  }
}

// Layer Mode Switching (MRI, U-Net Mask, Grad-CAM, Binary Mask)
function setViewMode(mode) {
  currentViewMode = mode;
  
  const buttons = {
    'original': 'btn-mode-orig',
    'segmentation': 'btn-mode-seg',
    'gradcam': 'btn-mode-cam',
    'mask_only': 'btn-mode-mask'
  };

  Object.entries(buttons).forEach(([m, id]) => {
    const btn = document.getElementById(id);
    if (btn) {
      if (m === mode) {
        btn.className = 'px-2.5 py-1 rounded font-medium bg-brand-600 text-white transition';
      } else {
        btn.className = 'px-2.5 py-1 rounded font-medium text-slate-300 hover:text-white transition';
      }
    }
  });

  updateViewerDisplay();
}

// Update Viewport based on current mode & data
function updateViewerDisplay() {
  if (!currentInferenceData || !currentInferenceData.visualizations) return;
  const imgEl = document.getElementById('viewerImage');
  const vis = currentInferenceData.visualizations;

  if (currentViewMode === 'original') {
    imgEl.src = vis.original_base64;
  } else if (currentViewMode === 'segmentation') {
    imgEl.src = vis.segmentation_overlay_base64;
  } else if (currentViewMode === 'gradcam') {
    imgEl.src = vis.gradcam_base64;
  } else if (currentViewMode === 'mask_only') {
    imgEl.src = vis.mask_base64;
  }
}

// Preset Sample Loader
async function loadSample(sampleKey) {
  currentSampleKey = sampleKey;
  currentUploadedFile = null;
  
  const formData = new FormData();
  formData.append('sample_key', sampleKey);
  formData.append('gradcam_alpha', currentGradcamAlpha);
  formData.append('mask_threshold', currentMaskThresh);

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
  formData.append('gradcam_alpha', currentGradcamAlpha);
  formData.append('mask_threshold', currentMaskThresh);

  await executeInference(formData);
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

// Render Diagnostic Cards, Probabilities & Quantitative Metrics
function renderDiagnosticResults(data) {
  const pred = data.prediction;
  const qm = data.quantitative_metrics;

  // Primary Label & Confidence
  const labelEl = document.getElementById('predictedLabel');
  const confEl = document.getElementById('confidenceScore');
  const descEl = document.getElementById('diagnosisDescription');
  const badgeEl = document.getElementById('tumorStatusBadge');

  if (labelEl) labelEl.textContent = pred.label;
  if (confEl) confEl.textContent = `${pred.confidence_percent}% Confidence`;
  if (descEl) descEl.textContent = pred.clinical_description;

  if (badgeEl) {
    if (pred.is_tumor_detected) {
      badgeEl.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-red-500/10 text-red-400 border border-red-500/20';
      badgeEl.textContent = 'LESION DETECTED';
    } else {
      badgeEl.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      badgeEl.textContent = 'NORMAL / NO LESION';
    }
  }

  // Softmax Probabilities Bars
  const probsContainer = document.getElementById('classProbabilities');
  if (probsContainer && pred.distribution) {
    probsContainer.innerHTML = '';
    Object.entries(pred.distribution).forEach(([cls, prob]) => {
      const isSelected = (cls === pred.label);
      const barColor = isSelected ? 'bg-brand-500' : 'bg-slate-700';
      const row = document.createElement('div');
      row.className = 'space-y-1';
      row.innerHTML = `
        <div class="flex justify-between text-[11px] ${isSelected ? 'text-white font-semibold' : 'text-slate-400'}">
          <span>${cls}</span>
          <span class="font-mono">${prob.toFixed(1)}%</span>
        </div>
        <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
          <div class="${barColor} h-1.5 rounded-full transition-all duration-500" style="width: ${prob}%"></div>
        </div>
      `;
      probsContainer.appendChild(row);
    });
  }

  // Quantitative Metrics
  document.getElementById('metricVolume').textContent = `${qm.estimated_volume_cm3} cm³`;
  document.getElementById('metricVolumeMm').textContent = `${qm.estimated_volume_mm3.toLocaleString()} mm³`;
  document.getElementById('metricArea').textContent = `${qm.surface_area_cm2} cm²`;
  document.getElementById('metricAreaMm').textContent = `${qm.surface_area_mm2.toLocaleString()} mm²`;
  document.getElementById('metricAxes').textContent = `${qm.major_axis_mm} × ${qm.minor_axis_mm} mm`;
  document.getElementById('metricSphericity').textContent = qm.sphericity_index;
}

// Slider Live Updates
function updateAlpha(val) {
  currentGradcamAlpha = parseFloat(val);
  document.getElementById('valAlpha').textContent = val;
  reRunInferenceWithParams();
}

function updateThreshold(val) {
  currentMaskThresh = parseFloat(val);
  document.getElementById('valThresh').textContent = val;
  reRunInferenceWithParams();
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
    formData.append('gradcam_alpha', currentGradcamAlpha);
    formData.append('mask_threshold', currentMaskThresh);
    await executeInference(formData);
  }, 120);
}

// Longitudinal Analysis Execution
async function runLongitudinalAnalysis() {
  try {
    const formData = new FormData();
    formData.append('baseline_sample', 'longitudinal_baseline');
    formData.append('followup_sample', 'longitudinal_followup');
    formData.append('days_between', '90');

    const res = await fetch('/api/longitudinal', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Longitudinal endpoint failed');
    const data = await res.json();

    const c = data.comparison;
    document.getElementById('longBaseVol').textContent = `${c.baseline.volume_cm3} cm³`;
    document.getElementById('longBaseArea').textContent = `${c.baseline.area_cm2} cm²`;
    document.getElementById('longFollowVol').textContent = `${c.followup.volume_cm3} cm³`;
    document.getElementById('longFollowArea').textContent = `${c.followup.area_cm2} cm²`;

    document.getElementById('longDeltaVol').textContent = `${c.delta_volume_cm3 > 0 ? '+' : ''}${c.delta_volume_cm3} cm³ (${c.percent_change_volume > 0 ? '+' : ''}${c.percent_change_volume}%)`;
    document.getElementById('longVelocity').textContent = `${c.growth_velocity_cm3_per_month} cm³/mo`;

    // Delta image map
    if (data.delta_map_base64) {
      document.getElementById('longDeltaImg').src = data.delta_map_base64;
    }

    // Verdict box
    document.getElementById('longVerdictTitle').textContent = `RANO Assessment: ${c.response_category}`;
    document.getElementById('longVerdictText').textContent = c.response_summary;

    const box = document.getElementById('longitudinalVerdictBox');
    if (c.trend === 'Regression') {
      box.className = 'p-4 rounded-xl bg-blue-950/40 border border-blue-500/30 flex items-start space-x-3';
    } else if (c.trend === 'Progression') {
      box.className = 'p-4 rounded-xl bg-red-950/40 border border-red-500/30 flex items-start space-x-3';
    } else {
      box.className = 'p-4 rounded-xl bg-amber-950/40 border border-amber-500/30 flex items-start space-x-3';
    }

    lucide.createIcons();
  } catch (err) {
    console.error('Longitudinal error:', err);
  }
}

// PDF Generation & Download
async function handleReportGenerate(e) {
  e.preventDefault();
  const btn = document.getElementById('btnGenerateReport');
  btn.disabled = true;
  btn.innerHTML = `<span>Generating Report PDF...</span>`;

  try {
    const formData = new FormData();
    formData.append('patient_name', document.getElementById('repPatientName').value);
    formData.append('patient_id', document.getElementById('repPatientId').value);
    formData.append('age_gender', document.getElementById('repAgeGender').value);
    formData.append('sample_key', document.getElementById('repSampleKey').value);
    formData.append('include_longitudinal', document.getElementById('repIncludeLong').checked);

    const res = await fetch('/api/report', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Report generation failed');
    const data = await res.json();

    const successBox = document.getElementById('reportSuccessBox');
    const dlLink = document.getElementById('reportDownloadLink');
    successBox.classList.remove('hidden');
    dlLink.href = data.download_url;
    
    // Automatically trigger download
    window.open(data.download_url, '_blank');
  } catch (err) {
    alert(`Could not generate report: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="download" class="w-4 h-4"></i><span>Generate & Download PDF Radiology Report</span>`;
    lucide.createIcons();
  }
}

function triggerPdfExport() {
  switchTab('report');
}
