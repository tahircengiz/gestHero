const DEFAULT_GESTURES = [
  { sequence: "D R", action: "close_tab" },
  { sequence: "U R", action: "new_tab" },
  { sequence: "U D", action: "reload_tab" },
  { sequence: "D L", action: "reopen_closed_tab" },
  { sequence: "L", action: "go_back" },
  { sequence: "R", action: "go_forward" },
  { sequence: "U", action: "scroll_top" },
  { sequence: "D", action: "scroll_bottom" },
];

const DEFAULT_SETTINGS = {
  mouseButton: "right",
  holdDelayMs: 180,
  minDistance: 20,
  minSpeed: 700,
  diagonalEnabled: true,
  diagonalBias: 1.4,
  cornerMinLength: 18,
  cornerToleranceDeg: 35,
  debugLog: false,
  trailColor: "#0078ff",
  trailWidth: 3,
  fadeDurationMs: 350,
  showDirection: true,
  testMode: false,
  showCheatSheet: false,
  disabledSites: "",
  zoomStep: 0.1,
  searchUrl: "https://www.google.com/search?q=%s",
};

const ACTIONS = [
  { value: "new_tab", label: "New Tab (Right)" },
  { value: "new_window", label: "New Window" },
  { value: "new_incognito_window", label: "New Incognito Window" },
  { value: "open_link_new_tab", label: "Open Link in New Tab" },
  {
    value: "open_link_background_tab",
    label: "Open Link in Background Tab (Right)",
  },
  { value: "open_link_new_window", label: "Open Link in New Window" },
  { value: "close_tab", label: "Close Tab" },
  { value: "reload_tab", label: "Reload Tab" },
  { value: "reopen_closed_tab", label: "Reopen Closed Tab" },
  { value: "duplicate_tab", label: "Duplicate Tab" },
  { value: "toggle_pin_tab", label: "Pin/Unpin Tab" },
  { value: "toggle_mute_tab", label: "Mute/Unmute Tab" },
  { value: "go_back", label: "Back" },
  { value: "go_forward", label: "Forward" },
  { value: "switch_tab_left", label: "Switch Tab Left" },
  { value: "switch_tab_right", label: "Switch Tab Right" },
  { value: "switch_tab_first", label: "Switch to First Tab" },
  { value: "switch_tab_last", label: "Switch to Last Tab" },
  { value: "move_tab_left", label: "Move Tab Left" },
  { value: "move_tab_right", label: "Move Tab Right" },
  { value: "zoom_in", label: "Zoom In" },
  { value: "zoom_out", label: "Zoom Out" },
  { value: "zoom_reset", label: "Zoom Reset" },
  { value: "toggle_fullscreen", label: "Toggle Fullscreen" },
  { value: "search_selected_text", label: "Search Selected Text" },
  { value: "copy_link_url", label: "Copy Link URL" },
  { value: "scroll_top", label: "Scroll Top" },
  { value: "scroll_bottom", label: "Scroll Bottom" },
];

const PRESETS = [
  { name: "Default", gestures: DEFAULT_GESTURES },
  {
    name: "Navigation",
    gestures: [
      { sequence: "L", action: "go_back" },
      { sequence: "R", action: "go_forward" },
      { sequence: "U", action: "new_tab" },
      { sequence: "D", action: "close_tab" },
      { sequence: "DR", action: "reload_tab" },
      { sequence: "DL", action: "reopen_closed_tab" },
      { sequence: "UR", action: "duplicate_tab" },
      { sequence: "UL", action: "toggle_pin_tab" },
    ],
  },
  {
    name: "Tab Manager",
    gestures: [
      { sequence: "L", action: "switch_tab_left" },
      { sequence: "R", action: "switch_tab_right" },
      { sequence: "U", action: "switch_tab_first" },
      { sequence: "D", action: "switch_tab_last" },
      { sequence: "DL", action: "move_tab_left" },
      { sequence: "DR", action: "move_tab_right" },
      { sequence: "UL", action: "toggle_mute_tab" },
      { sequence: "UR", action: "duplicate_tab" },
    ],
  },
  {
    name: "Link Power",
    gestures: [
      { sequence: "R", action: "open_link_new_tab" },
      { sequence: "D", action: "open_link_background_tab" },
      { sequence: "U", action: "open_link_new_window" },
      { sequence: "L", action: "copy_link_url" },
      { sequence: "DR", action: "search_selected_text" },
      { sequence: "UR", action: "new_tab" },
    ],
  },
];

const tableBody = document.getElementById("gesture-rows");
const addRowButton = document.getElementById("add-row");
const saveButton = document.getElementById("save");
const status = document.getElementById("status");
const presetSelect = document.getElementById("preset-select");
const applyPresetButton = document.getElementById("apply-preset");
const importFile = document.getElementById("import-file");
const exportButton = document.getElementById("export");

const minDistanceInput = document.getElementById("min-distance");
const minSpeedInput = document.getElementById("min-speed");
const mouseButtonSelect = document.getElementById("mouse-button");
const holdDelayInput = document.getElementById("hold-delay");
const diagonalEnabledInput = document.getElementById("diagonal-enabled");
const diagonalBiasInput = document.getElementById("diagonal-bias");
const cornerMinLengthInput = document.getElementById("corner-min-length");
const cornerToleranceInput = document.getElementById("corner-tolerance");
const showDirectionInput = document.getElementById("show-direction");
const testModeInput = document.getElementById("test-mode");
const cheatSheetInput = document.getElementById("cheat-sheet");
const debugLogInput = document.getElementById("debug-log");
const trailColorInput = document.getElementById("trail-color");
const trailWidthInput = document.getElementById("trail-width");
const fadeDurationInput = document.getElementById("fade-duration");
const zoomStepInput = document.getElementById("zoom-step");
const searchUrlInput = document.getElementById("search-url");
const disabledSitesInput = document.getElementById("disabled-sites");
const exportDebugButton = document.getElementById("export-debug");
const clearDebugButton = document.getElementById("clear-debug");

// Localised message lookup with a fallback (used before/if a key is missing).
function t(key, fallback, subs) {
  const msg =
    chrome.i18n && chrome.i18n.getMessage
      ? chrome.i18n.getMessage(key, subs)
      : "";
  return msg || fallback || "";
}

// Replace [data-i18n] text content with the localised message, keeping the
// HTML default as a fallback when a message is missing.
function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const msg = t(key, "");
    if (msg) {
      el.textContent = msg;
    }
  });
  const title = t("optionsTitle", "");
  if (title) {
    document.title = title;
  }
}

function setStatus(text, isWarn) {
  status.textContent = text;
  status.classList.toggle("warn", Boolean(isWarn));
  setTimeout(
    () => {
      status.textContent = "";
      status.classList.remove("warn");
    },
    isWarn ? 4000 : 1500,
  );
}

// Mark rows whose canonical sequence collides with another row and return the
// set of conflicting keys.
function highlightConflicts() {
  const rows = Array.from(tableBody.querySelectorAll("tr"));
  const gestures = rows.map((row) => ({
    sequence: row.querySelector("input").value,
    action: row.querySelector("select").value,
  }));
  const conflictKeys = new Set(
    GestureCore.findConflicts(gestures).map((item) => item.sequence),
  );
  rows.forEach((row) => {
    const input = row.querySelector("input");
    const key = GestureCore.normalizeForMatch(input.value);
    input.classList.toggle("conflict", Boolean(key) && conflictKeys.has(key));
  });
  return conflictKeys;
}

// Fullscreen capture overlay: draw a gesture with the mouse to fill the row's
// sequence field. Reuses the shared recogniser so it matches live detection.
function recordGesture(targetInput) {
  const opts = collectSettings();
  const overlay = document.createElement("div");
  overlay.className = "record-overlay";
  const canvas = document.createElement("canvas");
  canvas.className = "record-canvas";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const hint = document.createElement("div");
  hint.className = "record-hint";
  hint.textContent = t(
    "recordHint",
    "Draw the gesture, release to finish (Esc to cancel)",
  );
  overlay.appendChild(canvas);
  overlay.appendChild(hint);
  document.body.appendChild(overlay);

  const ctx = canvas.getContext("2d");
  ctx.strokeStyle = opts.trailColor || "#2563eb";
  ctx.lineWidth = Number(opts.trailWidth) || 3;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";

  let drawing = false;
  let points = [];

  function close() {
    window.removeEventListener("keydown", onKey, true);
    overlay.remove();
  }
  function onKey(event) {
    if (event.key === "Escape") {
      close();
    }
  }
  canvas.addEventListener("mousedown", (event) => {
    drawing = true;
    points = [{ x: event.clientX, y: event.clientY }];
    ctx.beginPath();
    ctx.moveTo(event.clientX, event.clientY);
  });
  canvas.addEventListener("mousemove", (event) => {
    if (!drawing) {
      return;
    }
    points.push({ x: event.clientX, y: event.clientY });
    ctx.lineTo(event.clientX, event.clientY);
    ctx.stroke();
  });
  canvas.addEventListener("mouseup", () => {
    if (!drawing) {
      return;
    }
    drawing = false;
    const tokens = GestureCore.recognizePoints(points, opts);
    close();
    if (!tokens.length) {
      setStatus(t("statusNoGesture", "No gesture detected."), true);
      return;
    }
    targetInput.value = GestureCore.formatSequence(tokens);
    highlightConflicts();
    setStatus(t("statusGestureRecorded", "Gesture recorded."));
  });
  window.addEventListener("keydown", onKey, true);
}

function normalizeSequence(sequence) {
  // Options keeps the un-collapsed form (e.g. "U U R") for display; the content
  // script collapses repeats when building its lookup map.
  return GestureCore.sanitizeTokens(sequence).join(" ");
}

function createActionSelect(selected) {
  const select = document.createElement("select");
  ACTIONS.forEach((action) => {
    const option = document.createElement("option");
    option.value = action.value;
    option.textContent = t("action_" + action.value, action.label);
    if (action.value === selected) {
      option.selected = true;
    }
    select.appendChild(option);
  });
  return select;
}

function addRow(sequence, action) {
  const row = document.createElement("tr");

  const seqCell = document.createElement("td");
  const input = document.createElement("input");
  input.type = "text";
  input.value = sequence || "";
  input.addEventListener("input", highlightConflicts);
  seqCell.appendChild(input);

  const actionCell = document.createElement("td");
  const select = createActionSelect(action || ACTIONS[0].value);
  select.addEventListener("change", highlightConflicts);
  actionCell.appendChild(select);

  const removeCell = document.createElement("td");
  removeCell.className = "row-actions";
  const drawButton = document.createElement("button");
  drawButton.textContent = t("draw", "Draw");
  drawButton.className = "ghost";
  drawButton.addEventListener("click", () => recordGesture(input));
  const removeButton = document.createElement("button");
  removeButton.textContent = t("remove", "Remove");
  removeButton.addEventListener("click", () => {
    row.remove();
    highlightConflicts();
  });
  removeCell.appendChild(drawButton);
  removeCell.appendChild(removeButton);

  row.appendChild(seqCell);
  row.appendChild(actionCell);
  row.appendChild(removeCell);
  tableBody.appendChild(row);
}

function setRows(gestures) {
  tableBody.innerHTML = "";
  (gestures || DEFAULT_GESTURES).forEach((item) => {
    addRow(item.sequence, item.action);
  });
}

function fillSettings(values) {
  const settings = { ...DEFAULT_SETTINGS, ...(values || {}) };
  mouseButtonSelect.value =
    settings.mouseButton || DEFAULT_SETTINGS.mouseButton;
  holdDelayInput.value = settings.holdDelayMs;
  minDistanceInput.value = settings.minDistance;
  minSpeedInput.value = settings.minSpeed;
  diagonalEnabledInput.checked = Boolean(settings.diagonalEnabled);
  diagonalBiasInput.value = settings.diagonalBias;
  cornerMinLengthInput.value = settings.cornerMinLength;
  cornerToleranceInput.value = settings.cornerToleranceDeg;
  showDirectionInput.checked = Boolean(settings.showDirection);
  testModeInput.checked = Boolean(settings.testMode);
  cheatSheetInput.checked = Boolean(settings.showCheatSheet);
  debugLogInput.checked = Boolean(settings.debugLog);
  trailColorInput.value = settings.trailColor;
  trailWidthInput.value = settings.trailWidth;
  fadeDurationInput.value = settings.fadeDurationMs;
  zoomStepInput.value = settings.zoomStep;
  searchUrlInput.value = settings.searchUrl;
  disabledSitesInput.value = settings.disabledSites;
}

function collectSettings() {
  const holdDelayValue = Number(holdDelayInput.value);
  return {
    mouseButton: mouseButtonSelect.value || DEFAULT_SETTINGS.mouseButton,
    holdDelayMs: Number.isNaN(holdDelayValue)
      ? DEFAULT_SETTINGS.holdDelayMs
      : Math.max(0, holdDelayValue),
    minDistance: Number(minDistanceInput.value) || DEFAULT_SETTINGS.minDistance,
    minSpeed: Number(minSpeedInput.value) || DEFAULT_SETTINGS.minSpeed,
    diagonalEnabled: diagonalEnabledInput.checked,
    diagonalBias:
      Number(diagonalBiasInput.value) || DEFAULT_SETTINGS.diagonalBias,
    cornerMinLength:
      Number(cornerMinLengthInput.value) || DEFAULT_SETTINGS.cornerMinLength,
    cornerToleranceDeg:
      Number(cornerToleranceInput.value) || DEFAULT_SETTINGS.cornerToleranceDeg,
    showDirection: showDirectionInput.checked,
    testMode: testModeInput.checked,
    showCheatSheet: cheatSheetInput.checked,
    debugLog: debugLogInput.checked,
    trailColor: trailColorInput.value || DEFAULT_SETTINGS.trailColor,
    trailWidth: Number(trailWidthInput.value) || DEFAULT_SETTINGS.trailWidth,
    fadeDurationMs:
      Number(fadeDurationInput.value) || DEFAULT_SETTINGS.fadeDurationMs,
    zoomStep: Number(zoomStepInput.value) || DEFAULT_SETTINGS.zoomStep,
    searchUrl: searchUrlInput.value || DEFAULT_SETTINGS.searchUrl,
    disabledSites: disabledSitesInput.value || "",
  };
}

function loadOptions() {
  chrome.storage.sync.get(
    { gestures: DEFAULT_GESTURES, settings: DEFAULT_SETTINGS },
    (data) => {
      setRows(data.gestures || DEFAULT_GESTURES);
      fillSettings(data.settings || DEFAULT_SETTINGS);
      highlightConflicts();
    },
  );
}

function saveOptions() {
  const rows = Array.from(tableBody.querySelectorAll("tr"));
  const gestures = rows
    .map((row) => {
      const input = row.querySelector("input");
      const select = row.querySelector("select");
      const normalized = normalizeSequence(input.value);
      input.value = normalized;
      return {
        sequence: normalized,
        action: select.value,
      };
    })
    .filter((item) => item.sequence);
  const settings = collectSettings();
  chrome.storage.sync.set({ gestures, settings }, () => {
    const conflictKeys = highlightConflicts();
    if (conflictKeys.size) {
      const list = Array.from(conflictKeys).join(", ");
      setStatus(
        t("statusDuplicate", `Saved. Duplicate gesture(s): ${list}`, [list]),
        true,
      );
    } else {
      setStatus(t("statusSaved", "Saved."));
    }
  });
}

function saveSettingsOnly() {
  const settings = collectSettings();
  chrome.storage.sync.set({ settings }, () => {
    setStatus(t("statusSettingsSaved", "Settings saved."));
  });
}

function populatePresets() {
  PRESETS.forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset.name;
    option.textContent = preset.name;
    presetSelect.appendChild(option);
  });
}

function applyPreset() {
  const selected = presetSelect.value;
  const preset = PRESETS.find((item) => item.name === selected);
  if (!preset) {
    return;
  }
  setRows(preset.gestures);
  highlightConflicts();
  setStatus(t("statusPresetLoaded", "Preset loaded."));
}

function exportSettings() {
  chrome.storage.sync.get(
    { gestures: DEFAULT_GESTURES, settings: DEFAULT_SETTINGS },
    (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "gesthero_settings.json";
      link.click();
      URL.revokeObjectURL(url);
      setStatus(t("statusExported", "Exported."));
    },
  );
}

function importSettings(file) {
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(reader.result);
      const gestures = Array.isArray(data.gestures)
        ? data.gestures
        : DEFAULT_GESTURES;
      const settings = { ...DEFAULT_SETTINGS, ...(data.settings || {}) };
      chrome.storage.sync.set({ gestures, settings }, () => {
        loadOptions();
        setStatus(t("statusImported", "Imported."));
      });
    } catch {
      setStatus(t("statusImportFailed", "Import failed."));
    }
  };
  reader.readAsText(file);
}

function exportDebugLog() {
  chrome.runtime.sendMessage({ type: "getDebugLog" }, (response) => {
    if (chrome.runtime.lastError) {
      setStatus(t("statusDebugUnavailable", "Debug log unavailable."));
      return;
    }
    const events = (response && response.events) || [];
    if (!events.length) {
      setStatus(t("statusNoEvents", "No events collected yet."));
    }
    const blob = new Blob([JSON.stringify({ events }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gesture_debug_log.json";
    link.click();
    URL.revokeObjectURL(url);
    setStatus(t("statusDebugExported", "Debug log exported."));
  });
}

function clearDebugLog() {
  chrome.runtime.sendMessage({ type: "clearDebugLog" }, () => {
    if (chrome.runtime.lastError) {
      setStatus(t("statusDebugUnavailable", "Debug log unavailable."));
      return;
    }
    setStatus(t("statusDebugCleared", "Debug log cleared."));
  });
}

addRowButton.addEventListener("click", () => addRow("", ACTIONS[0].value));
saveButton.addEventListener("click", saveOptions);
applyPresetButton.addEventListener("click", applyPreset);
exportButton.addEventListener("click", exportSettings);
exportDebugButton.addEventListener("click", exportDebugLog);
clearDebugButton.addEventListener("click", clearDebugLog);
debugLogInput.addEventListener("change", saveSettingsOnly);
importFile.addEventListener("change", () => {
  importSettings(importFile.files[0]);
});

applyI18n();
populatePresets();
loadOptions();
