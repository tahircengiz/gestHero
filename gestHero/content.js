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

const {
  simplifyTokens,
  formatSequence,
  getDirection,
  getAxisDistance,
  normalizeForMatch,
} = GestureCore;
const BUTTON_MAP = { left: 0, middle: 1, right: 2 };
const BUTTON_MASK_MAP = { 0: 1, 1: 4, 2: 2 };
const IS_MAC = (() => {
  const uaPlatform =
    navigator.userAgentData && navigator.userAgentData.platform;
  if (uaPlatform) {
    return /mac/i.test(uaPlatform);
  }
  if (navigator.platform) {
    return /mac/i.test(navigator.platform);
  }
  return /Mac/i.test(navigator.userAgent || "");
})();
const ACTIONS_LOCAL = new Set(["scroll_top", "scroll_bottom", "copy_link_url"]);
const LINK_ACTIONS = new Set([
  "open_link_new_tab",
  "open_link_background_tab",
  "open_link_new_window",
  "copy_link_url",
]);
const SELECTION_ACTIONS = new Set(["search_selected_text"]);

let gestureMap = new Map();
let settings = { ...DEFAULT_SETTINGS };
let gestureButton = BUTTON_MAP.right;
let disabledSiteList = [];
let debugEvents = [];
const DEBUG_LIMIT = 500;
let preventionListenersActive = false;
let macMenuTimer = null;
let macMenuArmed = false;

function blockEvent(event) {
  if (event.isTrusted) {
    event.preventDefault();
    event.stopPropagation();
  }
}

function enableContextMenuPrevention() {
  if (preventionListenersActive) return;
  preventionListenersActive = true;
  document.addEventListener("contextmenu", blockEvent, true);
  document.addEventListener("click", blockEvent, true);
  document.addEventListener("auxclick", blockEvent, true);
  logDebug("prevention_enabled", null);
}

function disableContextMenuPrevention() {
  if (!preventionListenersActive) return;
  preventionListenersActive = false;
  document.removeEventListener("contextmenu", blockEvent, true);
  document.removeEventListener("click", blockEvent, true);
  document.removeEventListener("auxclick", blockEvent, true);
  logDebug("prevention_disabled", null);
}

function buildGestureMap(gestures) {
  gestureMap = new Map();
  (gestures || []).forEach((item) => {
    const normalized = normalizeForMatch(item.sequence);
    if (normalized && item.action) {
      gestureMap.set(normalized, item.action);
    }
  });
}

function parseDisabledSites(value) {
  return String(value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function isSiteDisabled() {
  const host = window.location.hostname;
  if (!host || !disabledSiteList.length) {
    return false;
  }
  return disabledSiteList.some((pattern) => {
    const cleaned = pattern.replace(/^\*\./, "");
    if (!cleaned) {
      return false;
    }
    if (pattern.startsWith(".") || pattern.startsWith("*.")) {
      return host === cleaned || host.endsWith(`.${cleaned}`);
    }
    return host === cleaned || host.endsWith(`.${cleaned}`);
  });
}

function applySettings(nextSettings) {
  settings = { ...DEFAULT_SETTINGS, ...(nextSettings || {}) };
  gestureButton =
    BUTTON_MAP[settings.mouseButton] !== undefined
      ? BUTTON_MAP[settings.mouseButton]
      : BUTTON_MAP.right;
  disabledSiteList = parseDisabledSites(settings.disabledSites);
  updateCanvasStyle();
}

function isGestureButtonPressed(button, buttons) {
  if (typeof buttons !== "number") {
    return false;
  }
  const mask = BUTTON_MASK_MAP[button];
  if (!mask) {
    return false;
  }
  return (buttons & mask) !== 0;
}

function logDebug(type, data) {
  if (!settings.debugLog) {
    return;
  }
  const event = {
    t: Date.now(),
    type,
    data: data || null,
  };
  debugEvents.push(event);
  if (debugEvents.length > DEBUG_LIMIT) {
    debugEvents.shift();
  }
  chrome.runtime.sendMessage({ type: "debugEvent", event }, () => {
    void chrome.runtime.lastError;
  });
}

function loadSettings() {
  chrome.storage.sync.get(
    { gestures: DEFAULT_GESTURES, settings: DEFAULT_SETTINGS },
    (data) => {
      buildGestureMap(data.gestures || DEFAULT_GESTURES);
      applySettings(data.settings || DEFAULT_SETTINGS);
    },
  );
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "sync") {
    return;
  }
  if (changes.gestures) {
    buildGestureMap(changes.gestures.newValue || DEFAULT_GESTURES);
  }
  if (changes.settings) {
    applySettings(changes.settings.newValue || DEFAULT_SETTINGS);
  }
});

loadSettings();

let gestureActive = false;
let gestureUsed = false;
let pendingGesture = false;
let holdActivated = false;
let holdTimer = null;
let downTime = 0;
let pendingLastX = 0;
let pendingLastY = 0;
let allowContextMenuUntil = 0;
let suppressClickUntil = 0;
let directions = [];
let startX = 0;
let startY = 0;
let lastX = 0;
let lastY = 0;
let lastDrawX = 0;
let lastDrawY = 0;
let lastMoveTime = 0;
let segmentStartX = 0;
let segmentStartY = 0;
let pendingPoints = [];
let gestureContext = { linkUrl: null, selectionText: "" };
let canvas = null;
let ctx = null;
let labelEl = null;
let labelTimeout = null;
let cheatSheetEl = null;

function ensureLabel() {
  if (labelEl) {
    return;
  }
  labelEl = document.createElement("div");
  labelEl.style.position = "fixed";
  labelEl.style.top = "12px";
  labelEl.style.right = "12px";
  labelEl.style.padding = "6px 10px";
  labelEl.style.background = "rgba(0, 0, 0, 0.6)";
  labelEl.style.color = "#fff";
  labelEl.style.fontSize = "12px";
  labelEl.style.borderRadius = "4px";
  labelEl.style.zIndex = "2147483647";
  labelEl.style.pointerEvents = "none";
  labelEl.style.opacity = "0";
  labelEl.style.transition = "opacity 120ms ease";
  document.documentElement.appendChild(labelEl);
}

function showLabel(text, force) {
  if (!settings.showDirection && !force) {
    return;
  }
  ensureLabel();
  labelEl.textContent = text;
  labelEl.style.opacity = "1";
  if (labelTimeout) {
    clearTimeout(labelTimeout);
  }
}

function hideLabel(delay) {
  if (!labelEl) {
    return;
  }
  if (labelTimeout) {
    clearTimeout(labelTimeout);
  }
  labelTimeout = setTimeout(() => {
    if (!gestureActive) {
      labelEl.style.opacity = "0";
    }
  }, delay || 0);
}

function flashLabel(text, duration) {
  showLabel(text, true);
  hideLabel(duration || 1200);
}

function createCanvas() {
  canvas = document.createElement("canvas");
  canvas.style.position = "fixed";
  canvas.style.left = "0";
  canvas.style.top = "0";
  canvas.style.width = "100vw";
  canvas.style.height = "100vh";
  canvas.style.pointerEvents = "none";
  canvas.style.zIndex = "2147483647";
  canvas.style.opacity = "1";
  canvas.style.transition = "none";
  document.documentElement.appendChild(canvas);
  ctx = canvas.getContext("2d");
  resizeCanvas();
}

function updateCanvasStyle() {
  if (!ctx) {
    return;
  }
  ctx.lineWidth = Number(settings.trailWidth) || DEFAULT_SETTINGS.trailWidth;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.strokeStyle = settings.trailColor || DEFAULT_SETTINGS.trailColor;
}

function resizeCanvas() {
  if (!canvas || !ctx) {
    return;
  }
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
  updateCanvasStyle();
}

function fadeAndDestroyCanvas() {
  destroyCheatSheet();
  if (!canvas) {
    return;
  }
  const duration = Number(settings.fadeDurationMs) || 0;
  if (duration <= 0) {
    destroyCanvas();
    return;
  }
  canvas.style.transition = `opacity ${duration}ms ease`;
  canvas.style.opacity = "0";
  setTimeout(() => {
    destroyCanvas();
  }, duration);
}

function destroyCanvas() {
  destroyCheatSheet();
  if (canvas && canvas.parentNode) {
    canvas.parentNode.removeChild(canvas);
  }
  canvas = null;
  ctx = null;
}

function getActionLabel(action) {
  const msg =
    chrome.i18n && chrome.i18n.getMessage
      ? chrome.i18n.getMessage("action_" + action)
      : "";
  return msg || action;
}

// Reference panel listing the configured gestures while one is being drawn.
function showCheatSheet() {
  if (!settings.showCheatSheet || cheatSheetEl) {
    return;
  }
  const entries = Array.from(gestureMap.entries());
  if (!entries.length) {
    return;
  }
  cheatSheetEl = document.createElement("div");
  cheatSheetEl.style.position = "fixed";
  cheatSheetEl.style.left = "12px";
  cheatSheetEl.style.bottom = "12px";
  cheatSheetEl.style.maxHeight = "60vh";
  cheatSheetEl.style.overflow = "auto";
  cheatSheetEl.style.padding = "10px 12px";
  cheatSheetEl.style.background = "rgba(0, 0, 0, 0.78)";
  cheatSheetEl.style.color = "#fff";
  cheatSheetEl.style.font = "12px/1.5 system-ui, sans-serif";
  cheatSheetEl.style.borderRadius = "8px";
  cheatSheetEl.style.zIndex = "2147483647";
  cheatSheetEl.style.pointerEvents = "none";
  const title = document.createElement("div");
  title.textContent =
    (chrome.i18n &&
      chrome.i18n.getMessage &&
      chrome.i18n.getMessage("cheatSheetTitle")) ||
    "Gestures";
  title.style.fontWeight = "600";
  title.style.marginBottom = "4px";
  cheatSheetEl.appendChild(title);
  entries.forEach(([sequence, action]) => {
    const rowEl = document.createElement("div");
    rowEl.textContent = `${sequence}  →  ${getActionLabel(action)}`;
    cheatSheetEl.appendChild(rowEl);
  });
  document.documentElement.appendChild(cheatSheetEl);
}

function destroyCheatSheet() {
  if (cheatSheetEl && cheatSheetEl.parentNode) {
    cheatSheetEl.parentNode.removeChild(cheatSheetEl);
  }
  cheatSheetEl = null;
}

function findLinkHref(target) {
  let element = target;
  if (element && element.nodeType === 3) {
    element = element.parentElement;
  }
  if (element && element.closest) {
    const anchor = element.closest("a[href]");
    if (anchor && anchor.href) {
      return anchor.href;
    }
  }
  return null;
}

function getSelectionText() {
  const selection = window.getSelection();
  return selection ? selection.toString().trim() : "";
}

function copyText(text) {
  if (!text) {
    return false;
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text);
    return true;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
    return true;
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

function performLocalAction(action) {
  if (action === "scroll_top") {
    window.scrollTo({ top: 0, behavior: "smooth" });
    return true;
  }
  if (action === "scroll_bottom") {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: "smooth",
    });
    return true;
  }
  if (action === "copy_link_url") {
    return copyText(gestureContext.linkUrl);
  }
  return false;
}

function cancelGesture() {
  gestureActive = false;
  gestureUsed = false;
  pendingGesture = false;
  holdActivated = false;
  if (holdTimer) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
  directions = [];
  gestureContext = { linkUrl: null, selectionText: "" };
  startX = 0;
  startY = 0;
  downTime = 0;
  pendingLastX = 0;
  pendingLastY = 0;
  allowContextMenuUntil = 0;
  pendingPoints = [];
  segmentStartX = 0;
  segmentStartY = 0;
  logDebug("cancel", null);
  fadeAndDestroyCanvas();
  hideLabel(0);
  disableContextMenuPrevention();
}

function handlePendingRelease(now, source) {
  const delayValue = Number(settings.holdDelayMs);
  const delay = Number.isNaN(delayValue)
    ? DEFAULT_SETTINGS.holdDelayMs
    : delayValue;
  if (IS_MAC && gestureButton === 2 && now - downTime < delay) {
    // On macOS, contextmenu is handled via double right-click.
  } else if (now - downTime < delay) {
    allowContextMenuUntil = now + 350;
    triggerContextMenu(startX, startY);
  } else {
    suppressClickUntil = now + 500;
  }
  pendingGesture = false;
  holdActivated = false;
  if (holdTimer) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
  directions = [];
  gestureContext = { linkUrl: null, selectionText: "" };
  startX = 0;
  startY = 0;
  pendingLastX = 0;
  pendingLastY = 0;
  pendingPoints = [];
  segmentStartX = 0;
  segmentStartY = 0;
  destroyCanvas();
  hideLabel(0);
  logDebug("pending_release", {
    source: source || "unknown",
    elapsed: Math.round(now - downTime),
  });
}

function finalizeGesture(options) {
  const opts = options || {};
  if (opts.suppressClick) {
    suppressClickUntil = performance.now() + 500;
  }
  gestureActive = false;
  pendingGesture = false;
  const wasHold = holdActivated;
  holdActivated = false;
  if (holdTimer) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
  gestureContext.selectionText = getSelectionText();
  const simplifiedTokens = simplifyTokens(directions);
  const sequence = formatSequence(simplifiedTokens);
  if (sequence) {
    handleGesture(sequence);
  }
  logDebug("up", {
    sequence,
    raw: directions.slice(0),
    simplified: simplifiedTokens,
    hold: wasHold,
    source: opts.source || "mouseup",
  });
  fadeAndDestroyCanvas();
  hideLabel(settings.testMode ? 1500 : 0);
  gestureContext = { linkUrl: null, selectionText: "" };
  directions = [];
  startX = 0;
  startY = 0;
  pendingLastX = 0;
  pendingLastY = 0;
  pendingPoints = [];
  segmentStartX = 0;
  segmentStartY = 0;
  gestureUsed = false;
  setTimeout(() => {
    if (!gestureActive && !pendingGesture) {
      disableContextMenuPrevention();
    }
  }, 200);
}

function triggerContextMenu(x, y) {
  if (IS_MAC) {
    logDebug("context_menu_trigger_skipped", { reason: "mac" });
    return;
  }
  const target = document.elementFromPoint(x, y);
  if (!target) {
    logDebug("context_menu_trigger_failed", { reason: "no_target" });
    return;
  }
  const event = new MouseEvent("contextmenu", {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 2,
  });
  const dispatched = target.dispatchEvent(event);
  logDebug("context_menu_triggered", { dispatched: Boolean(dispatched) });
}

function activateGesture(x, y, mode) {
  if (gestureActive) {
    return false;
  }
  gestureActive = true;
  pendingGesture = false;
  holdActivated = mode === "hold";
  if (holdTimer) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
  directions = [];
  segmentStartX = x;
  segmentStartY = y;
  lastX = x;
  lastY = y;
  lastDrawX = x;
  lastDrawY = y;
  lastMoveTime = performance.now();
  createCanvas();
  showCheatSheet();
  if (settings.showDirection) {
    showLabel("");
  }
  enableContextMenuPrevention();
  logDebug("activate", { mode, x, y });
  return true;
}

function processGestureMove(x, y, now) {
  const dx = x - lastX;
  const dy = y - lastY;
  const distance = Math.hypot(dx, dy);
  const dxSegment = x - segmentStartX;
  const dySegment = y - segmentStartY;
  const segmentDistance = Math.hypot(dxSegment, dySegment);
  const deltaTime = now - lastMoveTime;
  const speed = deltaTime > 0 ? distance / (deltaTime / 1000) : 0;
  const minDistance =
    Number(settings.minDistance) || DEFAULT_SETTINGS.minDistance;
  const minSpeed = Number(settings.minSpeed) || 0;
  if (distance < minDistance && speed < minSpeed) {
    return;
  }
  gestureUsed = true;
  const absSegmentX = Math.abs(dxSegment);
  const absSegmentY = Math.abs(dySegment);
  const direction = getDirection(dxSegment, dySegment, settings);
  if (direction) {
    const lastDirection = directions[directions.length - 1];
    const cornerMinLength =
      Number(settings.cornerMinLength) || DEFAULT_SETTINGS.cornerMinLength;
    const axisDistance = getAxisDistance(direction, absSegmentX, absSegmentY);
    let committed = false;
    if (!lastDirection) {
      if (axisDistance >= minDistance) {
        directions.push(direction);
        committed = true;
      }
    } else if (direction !== lastDirection) {
      if (axisDistance >= cornerMinLength) {
        directions.push(direction);
        committed = true;
      }
    }
    logDebug("eval", {
      direction,
      lastDirection: lastDirection || null,
      axisDistance: Math.round(axisDistance),
      segmentDistance: Math.round(segmentDistance),
      committed,
    });
    if (committed) {
      segmentStartX = x;
      segmentStartY = y;
    }
    if (settings.showDirection) {
      showLabel(formatSequence(simplifyTokens(directions)));
    }
  }
  if (ctx) {
    ctx.beginPath();
    ctx.moveTo(lastDrawX, lastDrawY);
    ctx.lineTo(x, y);
    ctx.stroke();
  }
  lastX = x;
  lastY = y;
  lastDrawX = x;
  lastDrawY = y;
  lastMoveTime = now;
}

function replayPendingPoints() {
  if (!pendingPoints.length) {
    return;
  }
  const first = pendingPoints[0];
  lastX = first.x;
  lastY = first.y;
  lastDrawX = first.x;
  lastDrawY = first.y;
  lastMoveTime = first.t;
  segmentStartX = first.x;
  segmentStartY = first.y;
  for (let i = 1; i < pendingPoints.length; i += 1) {
    const point = pendingPoints[i];
    processGestureMove(point.x, point.y, point.t);
  }
  pendingPoints = [];
}

function handleGesture(sequence) {
  const action = gestureMap.get(sequence);
  if (settings.testMode) {
    flashLabel(
      action
        ? `Gesture ${sequence} -> ${action}`
        : `Gesture ${sequence} -> none`,
    );
    return;
  }
  if (!action) {
    return;
  }
  if (ACTIONS_LOCAL.has(action)) {
    performLocalAction(action);
    return;
  }
  if (LINK_ACTIONS.has(action) && !gestureContext.linkUrl) {
    return;
  }
  if (SELECTION_ACTIONS.has(action) && !gestureContext.selectionText) {
    return;
  }
  const payload = {
    type: "executeAction",
    action,
    zoomStep: settings.zoomStep,
    searchUrl: settings.searchUrl,
  };
  if (gestureContext.linkUrl) {
    payload.linkUrl = gestureContext.linkUrl;
  }
  if (gestureContext.selectionText) {
    payload.selectionText = gestureContext.selectionText;
  }
  chrome.runtime.sendMessage(payload, () => {
    void chrome.runtime.lastError;
  });
}

function onMouseDown(event) {
  if (event.button !== gestureButton) {
    return;
  }
  if (isSiteDisabled()) {
    return;
  }
  if (gestureButton !== 2) {
    event.preventDefault();
  }
  gestureUsed = false;
  directions = [];
  gestureContext = {
    linkUrl: findLinkHref(event.target),
    selectionText: getSelectionText(),
  };
  startX = event.clientX;
  startY = event.clientY;
  pendingLastX = startX;
  pendingLastY = startY;
  lastX = startX;
  lastY = startY;
  lastDrawX = startX;
  lastDrawY = startY;
  lastMoveTime = performance.now();
  downTime = lastMoveTime;
  segmentStartX = startX;
  segmentStartY = startY;
  pendingPoints = [{ x: startX, y: startY, t: downTime }];
  logDebug("down", {
    button: event.button,
    x: startX,
    y: startY,
    link: Boolean(gestureContext.linkUrl),
    selection: Boolean(gestureContext.selectionText),
  });
  if (gestureButton === 2) {
    pendingGesture = true;
    holdActivated = false;
    allowContextMenuUntil = 0;
    if (holdTimer) {
      clearTimeout(holdTimer);
      holdTimer = null;
    }
    const delayValue = Number(settings.holdDelayMs);
    const delay = Number.isNaN(delayValue)
      ? DEFAULT_SETTINGS.holdDelayMs
      : delayValue;
    holdTimer = setTimeout(
      () => {
        if (!pendingGesture || gestureActive) {
          return;
        }
        if (activateGesture(startX, startY, "hold")) {
          replayPendingPoints();
        }
      },
      Math.max(0, delay),
    );
    return;
  }
  activateGesture(startX, startY, "immediate");
}

function onMouseMove(event) {
  if (
    gestureButton !== 2 &&
    (gestureActive || pendingGesture) &&
    !isGestureButtonPressed(gestureButton, event.buttons)
  ) {
    if (pendingGesture && !gestureActive) {
      handlePendingRelease(performance.now(), "move");
    } else if (gestureActive) {
      finalizeGesture({
        suppressClick: gestureUsed || holdActivated,
        source: "move",
      });
    }
    return;
  }
  if (!gestureActive) {
    if (!pendingGesture) {
      return;
    }
    pendingLastX = event.clientX;
    pendingLastY = event.clientY;
    const now = performance.now();
    pendingPoints.push({ x: pendingLastX, y: pendingLastY, t: now });
    if (pendingPoints.length > 200) {
      pendingPoints.shift();
    }
    const delayValue = Number(settings.holdDelayMs);
    const delay = Number.isNaN(delayValue)
      ? DEFAULT_SETTINGS.holdDelayMs
      : delayValue;
    const elapsed = now - downTime;
    if (elapsed < delay) {
      return;
    }
    if (activateGesture(startX, startY, "hold")) {
      replayPendingPoints();
    }
    return;
  }
  processGestureMove(event.clientX, event.clientY, performance.now());
  event.preventDefault();
}

function onMouseUp(event) {
  if (!gestureActive && !pendingGesture) {
    return;
  }
  if (
    gestureButton !== 2 &&
    isGestureButtonPressed(gestureButton, event.buttons)
  ) {
    return;
  }
  if (pendingGesture && !gestureActive) {
    handlePendingRelease(performance.now(), "mouseup");
    return;
  }
  const shouldSuppress = gestureUsed || holdActivated;
  if (shouldSuppress) {
    event.preventDefault();
    event.stopPropagation();
  }
  finalizeGesture({
    suppressClick: shouldSuppress,
    source: "mouseup",
  });
}

function onContextMenu(event) {
  if (gestureButton !== 2) {
    return;
  }
  const now = performance.now();

  if (IS_MAC) {
    if (macMenuArmed) {
      macMenuArmed = false;
      if (macMenuTimer) {
        clearTimeout(macMenuTimer);
        macMenuTimer = null;
      }
      cancelGesture();
      logDebug("context_menu_mac_allowed", { windowMs: 500 });
      return;
    }
    macMenuArmed = true;
    if (macMenuTimer) {
      clearTimeout(macMenuTimer);
    }
    macMenuTimer = setTimeout(() => {
      macMenuArmed = false;
      macMenuTimer = null;
    }, 500);
    event.preventDefault();
    event.stopPropagation();
    logDebug("context_menu_mac_deferred", { windowMs: 500 });
    return;
  }

  // Allow menu if explicitly permitted (after quick release)
  if (allowContextMenuUntil && now <= allowContextMenuUntil) {
    allowContextMenuUntil = 0;
    logDebug("context_menu_allowed", { elapsed: Math.round(now - downTime) });
    return;
  }

  // Block if suppressClickUntil is active (after gesture completes)
  if (now < suppressClickUntil) {
    event.preventDefault();
    event.stopPropagation();
    logDebug("context_menu_suppressed", {
      suppressedUntil: Math.round(suppressClickUntil - now),
    });
    return;
  }

  if (pendingGesture) {
    const delayValue = Number(settings.holdDelayMs);
    const delay = Number.isNaN(delayValue)
      ? DEFAULT_SETTINGS.holdDelayMs
      : delayValue;
    const elapsed = now - downTime;
    if (elapsed < delay) {
      event.preventDefault();
      event.stopPropagation();
      logDebug("context_menu_deferred", { elapsed: Math.round(elapsed) });
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    logDebug("context_menu_suppressed", { elapsed: Math.round(elapsed) });
    return;
  }

  // If gesture is already active, dynamic listeners will handle it
  if (gestureActive) {
    return;
  }

  // No gesture state - allow menu to open
}

function onClickCapture(event) {
  if (performance.now() > suppressClickUntil) {
    return;
  }
  if (event.button !== gestureButton) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
}

chrome.runtime.onMessage.addListener((message) => {
  if (!message || message.type !== "historyNavigate") {
    return;
  }
  if (message.direction === "back") {
    history.back();
  } else if (message.direction === "forward") {
    history.forward();
  }
});

window.addEventListener("resize", resizeCanvas);
document.addEventListener("mousedown", onMouseDown, true);
document.addEventListener("mousemove", onMouseMove, true);
document.addEventListener("mouseup", onMouseUp, true);
document.addEventListener("click", onClickCapture, true);
document.addEventListener("auxclick", onClickCapture, true);
document.addEventListener("contextmenu", onContextMenu, true);
function handleWindowBlur(source) {
  if (gestureButton === 2) {
    if (pendingGesture && !gestureActive) {
      handlePendingRelease(performance.now(), source || "blur");
      return;
    }
    if (gestureActive) {
      finalizeGesture({
        suppressClick: gestureUsed || holdActivated,
        source: source || "blur",
      });
      return;
    }
  }
  cancelGesture();
}

window.addEventListener("blur", () => handleWindowBlur("blur"));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    handleWindowBlur("visibility");
  }
});
