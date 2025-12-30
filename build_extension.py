#!/usr/bin/env python3
import base64
import copy
import json
import os
import shutil
import subprocess
import textwrap


ICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)


MANIFEST = {
    "name": "Simple Gestures",
    "description": "Lightweight mouse gesture controls.",
    "version": "1.0.0",
    "manifest_version": 3,
    "permissions": ["storage", "tabs", "sessions", "windows"],
    "host_permissions": ["<all_urls>"],
    "background": {"service_worker": "background.js"},
    "action": {
        "default_title": "Simple Gestures",
        "default_icon": {
            "16": "icon16.png",
            "48": "icon48.png",
            "128": "icon128.png",
        },
    },
    "icons": {
        "16": "icon16.png",
        "48": "icon48.png",
        "128": "icon128.png",
    },
    "options_page": "options.html",
    "content_scripts": [
        {
            "matches": ["<all_urls>"],
            "js": ["content.js"],
            "run_at": "document_idle",
        }
    ],
}


BACKGROUND_JS = textwrap.dedent(
    """
    const DEFAULT_SEARCH_URL = "https://www.google.com/search?q=%s";
    const DEFAULT_ZOOM_STEP = 0.1;
    const DEBUG_LIMIT = 500;
    let debugEvents = [];

    const getInsertIndex = (tab) =>
      tab && typeof tab.index === "number" ? tab.index + 1 : undefined;

    function createTabNextTo(tab, options) {
      const index = getInsertIndex(tab);
      if (typeof index === "number") {
        options.index = index;
      }
      chrome.tabs.create(options);
    }

    function buildSearchUrl(query, template) {
      if (!query) {
        return null;
      }
      const safeQuery = encodeURIComponent(query);
      const base = template || DEFAULT_SEARCH_URL;
      if (base.includes("%s")) {
        return base.replace("%s", safeQuery);
      }
      return `${base}${safeQuery}`;
    }

    function openSearchTab(query, template) {
      const url = buildSearchUrl(query, template);
      if (!url) {
        return;
      }
      chrome.tabs.create({ url });
    }

    function switchTab(offset, tab) {
      if (!tab || typeof tab.index !== "number") {
        return;
      }
      chrome.tabs.query({ currentWindow: true }, (tabs) => {
        if (!tabs || !tabs.length) {
          return;
        }
        let targetIndex = tab.index + offset;
        if (targetIndex < 0) {
          targetIndex = tabs.length - 1;
        } else if (targetIndex >= tabs.length) {
          targetIndex = 0;
        }
        const target = tabs.find((item) => item.index === targetIndex);
        if (target && target.id) {
          chrome.tabs.update(target.id, { active: true });
        }
      });
    }

    function switchTabEdge(edge, tab) {
      if (!tab) {
        return;
      }
      chrome.tabs.query({ currentWindow: true }, (tabs) => {
        if (!tabs || !tabs.length) {
          return;
        }
        const target = edge === "first" ? tabs[0] : tabs[tabs.length - 1];
        if (target && target.id) {
          chrome.tabs.update(target.id, { active: true });
        }
      });
    }

    function moveTab(offset, tab) {
      if (!tab || typeof tab.index !== "number" || !tab.id) {
        return;
      }
      chrome.tabs.query({ currentWindow: true }, (tabs) => {
        if (!tabs || !tabs.length) {
          return;
        }
        const maxIndex = tabs.length - 1;
        const targetIndex = Math.min(
          maxIndex,
          Math.max(0, tab.index + offset)
        );
        chrome.tabs.move(tab.id, { index: targetIndex });
      });
    }

    function togglePin(tab) {
      if (!tab || !tab.id) {
        return;
      }
      chrome.tabs.update(tab.id, { pinned: !tab.pinned });
    }

    function toggleMute(tab) {
      if (!tab || !tab.id || !tab.mutedInfo) {
        return;
      }
      chrome.tabs.update(tab.id, { muted: !tab.mutedInfo.muted });
    }

    function changeZoom(tab, deltaSteps, zoomStep) {
      if (!tab || !tab.id) {
        return;
      }
      const step = Number(zoomStep) || DEFAULT_ZOOM_STEP;
      chrome.tabs.getZoom(tab.id, (zoom) => {
        if (chrome.runtime.lastError) {
          return;
        }
        const nextZoom = Math.min(5, Math.max(0.25, zoom + deltaSteps * step));
        chrome.tabs.setZoom(tab.id, nextZoom);
      });
    }

    function resetZoom(tab) {
      if (!tab || !tab.id) {
        return;
      }
      chrome.tabs.setZoom(tab.id, 1);
    }

    function navigateHistory(tab, direction) {
      if (!tab || !tab.id) {
        return;
      }
      if (direction === "back" && chrome.tabs.goBack) {
        chrome.tabs.goBack(tab.id);
        return;
      }
      if (direction === "forward" && chrome.tabs.goForward) {
        chrome.tabs.goForward(tab.id);
        return;
      }
      chrome.tabs.sendMessage(tab.id, { type: "historyNavigate", direction });
    }

    function toggleFullscreen(tab) {
      if (!tab || typeof tab.windowId !== "number") {
        return;
      }
      chrome.windows.get(tab.windowId, {}, (win) => {
        if (!win) {
          return;
        }
        const nextState = win.state === "fullscreen" ? "normal" : "fullscreen";
        chrome.windows.update(win.id, { state: nextState });
      });
    }

    const ACTIONS = {
      new_tab: (tab) => {
        createTabNextTo(tab, { url: "chrome://newtab", active: true });
      },
      new_window: () => {
        chrome.windows.create({ url: "chrome://newtab", focused: true });
      },
      new_incognito_window: () => {
        chrome.windows.create({
          url: "chrome://newtab",
          focused: true,
          incognito: true,
        });
      },
      open_link_new_tab: (tab, message) => {
        if (!message.linkUrl) {
          return;
        }
        createTabNextTo(tab, { url: message.linkUrl, active: true });
      },
      open_link_background_tab: (tab, message) => {
        if (!message.linkUrl) {
          return;
        }
        createTabNextTo(tab, { url: message.linkUrl, active: false });
      },
      open_link_new_window: (tab, message) => {
        if (!message.linkUrl) {
          return;
        }
        chrome.windows.create({ url: message.linkUrl, focused: true });
      },
      close_tab: (tab) => {
        if (tab && tab.id) {
          chrome.tabs.remove(tab.id);
        }
      },
      reload_tab: (tab) => {
        if (tab && tab.id) {
          chrome.tabs.reload(tab.id);
        }
      },
      reopen_closed_tab: () => {
        chrome.sessions.restore();
      },
      duplicate_tab: (tab) => {
        if (tab && tab.id) {
          chrome.tabs.duplicate(tab.id);
        }
      },
      toggle_pin_tab: (tab) => {
        togglePin(tab);
      },
      toggle_mute_tab: (tab) => {
        toggleMute(tab);
      },
      switch_tab_right: (tab) => {
        switchTab(1, tab);
      },
      switch_tab_left: (tab) => {
        switchTab(-1, tab);
      },
      switch_tab_first: (tab) => {
        switchTabEdge("first", tab);
      },
      switch_tab_last: (tab) => {
        switchTabEdge("last", tab);
      },
      move_tab_right: (tab) => {
        moveTab(1, tab);
      },
      move_tab_left: (tab) => {
        moveTab(-1, tab);
      },
      go_back: (tab) => {
        navigateHistory(tab, "back");
      },
      go_forward: (tab) => {
        navigateHistory(tab, "forward");
      },
      zoom_in: (tab, message) => {
        changeZoom(tab, 1, message.zoomStep);
      },
      zoom_out: (tab, message) => {
        changeZoom(tab, -1, message.zoomStep);
      },
      zoom_reset: (tab) => {
        resetZoom(tab);
      },
      toggle_fullscreen: (tab) => {
        toggleFullscreen(tab);
      },
      search_selected_text: (tab, message) => {
        if (!message.selectionText) {
          return;
        }
        openSearchTab(message.selectionText, message.searchUrl);
      },
    };

    function addDebugEvent(event) {
      if (!event) {
        return;
      }
      debugEvents.push(event);
      if (debugEvents.length > DEBUG_LIMIT) {
        debugEvents.shift();
      }
    }

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (!message || !message.type) {
        return;
      }
      if (message.type === "executeAction") {
        const action = ACTIONS[message.action];
        if (action) {
          action(sender.tab, message);
        }
        return;
      }
      if (message.type === "debugEvent") {
        addDebugEvent(message.event);
        return;
      }
      if (message.type === "getDebugLog") {
        sendResponse({ events: debugEvents });
        return;
      }
      if (message.type === "clearDebugLog") {
        debugEvents = [];
        sendResponse({ ok: true });
      }
    });
    """
).strip() + "\n"


CONTENT_JS = textwrap.dedent(
    """
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
      disabledSites: "",
      zoomStep: 0.1,
      searchUrl: "https://www.google.com/search?q=%s",
    };

    const VALID_TOKENS = new Set(["U", "D", "L", "R", "UR", "UL", "DR", "DL"]);
    const BUTTON_MAP = { left: 0, middle: 1, right: 2 };
    const BUTTON_MASK_MAP = { 0: 1, 1: 4, 2: 2 };
    const IS_MAC = /Mac/i.test(navigator.platform);
    const ACTIONS_LOCAL = new Set([
      "scroll_top",
      "scroll_bottom",
      "copy_link_url",
    ]);
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

    function tokenizeSequence(value) {
      const raw = String(value || "").trim().toUpperCase();
      if (!raw) {
        return [];
      }
      if (/[\s,>-]/.test(raw)) {
        return raw.split(/[\s,>-]+/).filter(Boolean);
      }
      if (raw.length === 2 && VALID_TOKENS.has(raw)) {
        return [raw];
      }
      return raw.split("");
    }

    function collapseRepeats(tokens) {
      const result = [];
      let last = null;
      tokens.forEach((token) => {
        if (token && token !== last) {
          result.push(token);
          last = token;
        }
      });
      return result;
    }

    function simplifyTokens(tokens) {
      const collapsed = collapseRepeats(tokens);
      const result = [];
      for (let i = 0; i < collapsed.length; i += 1) {
        const token = collapsed[i];
        if (!token || token.length !== 2) {
          result.push(token);
          continue;
        }
        const prev = result[result.length - 1];
        const next = collapsed[i + 1];
        const prevCardinal = prev && prev.length === 1;
        const nextCardinal = next && next.length === 1;
        const matchesPrev = prevCardinal && token.includes(prev);
        const matchesNext = nextCardinal && token.includes(next);
        if (matchesPrev && matchesNext) {
          continue;
        }
        if (matchesPrev && !nextCardinal) {
          const replacement = token.replace(prev, "");
          if (replacement.length === 1) {
            result.push(replacement);
            continue;
          }
        }
        result.push(token);
      }
      return result;
    }

    function normalizeSequence(sequence) {
      const tokens = tokenizeSequence(sequence)
        .map((token) => token.replace(/[^UDLR]/g, ""))
        .filter((token) => VALID_TOKENS.has(token));
      return collapseRepeats(tokens).join(" ");
    }

    function formatSequence(tokens) {
      return tokens.join(" ");
    }

    function buildGestureMap(gestures) {
      gestureMap = new Map();
      (gestures || []).forEach((item) => {
        const normalized = normalizeSequence(item.sequence);
        if (normalized && item.action) {
          gestureMap.set(normalized, item.action);
        }
      });
    }

    function parseDisabledSites(value) {
      return String(value || "")
        .split(/[\\n,]+/)
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
      chrome.runtime.sendMessage({ type: "debugEvent", event });
    }

    function loadSettings() {
      chrome.storage.sync.get(
        { gestures: DEFAULT_GESTURES, settings: DEFAULT_SETTINGS },
        (data) => {
          buildGestureMap(data.gestures || DEFAULT_GESTURES);
          applySettings(data.settings || DEFAULT_SETTINGS);
        }
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
      if (canvas && canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
      canvas = null;
      ctx = null;
    }

    function getDirection(dx, dy) {
      const absX = Math.abs(dx);
      const absY = Math.abs(dy);
      if (absX === 0 && absY === 0) {
        return null;
      }
      if (!settings.diagonalEnabled) {
        return absX >= absY ? (dx > 0 ? "R" : "L") : dy > 0 ? "D" : "U";
      }
      const bias = Math.max(1, Number(settings.diagonalBias) || 1);
      const tolerance = Math.max(0, Number(settings.cornerToleranceDeg) || 0);
      if (absY === 0) {
        return dx > 0 ? "R" : "L";
      }
      if (absX === 0) {
        return dy > 0 ? "D" : "U";
      }
      const angle = (Math.atan2(absY, absX) * 180) / Math.PI;
      if (angle <= tolerance) {
        return dx > 0 ? "R" : "L";
      }
      if (angle >= 90 - tolerance) {
        return dy > 0 ? "D" : "U";
      }
      if (absX >= absY * bias) {
        return dx > 0 ? "R" : "L";
      }
      if (absY >= absX * bias) {
        return dy > 0 ? "D" : "U";
      }
      if (dx > 0 && dy > 0) {
        return "DR";
      }
      if (dx > 0 && dy < 0) {
        return "UR";
      }
      if (dx < 0 && dy > 0) {
        return "DL";
      }
      return "UL";
    }

    function getAxisDistance(direction, absX, absY) {
      if (!direction) {
        return 0;
      }
      if (direction === "L" || direction === "R") {
        return absX;
      }
      if (direction === "U" || direction === "D") {
        return absY;
      }
      return Math.min(absX, absY);
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
      } catch (error) {
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
      const minDistance = Number(settings.minDistance) || DEFAULT_SETTINGS.minDistance;
      const minSpeed = Number(settings.minSpeed) || 0;
      if (distance < minDistance && speed < minSpeed) {
        return;
      }
      gestureUsed = true;
      const absSegmentX = Math.abs(dxSegment);
      const absSegmentY = Math.abs(dySegment);
      const direction = getDirection(dxSegment, dySegment);
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
          action ? `Gesture ${sequence} -> ${action}` : `Gesture ${sequence} -> none`
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
      chrome.runtime.sendMessage(payload);
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
        holdTimer = setTimeout(() => {
          if (!pendingGesture || gestureActive) {
            return;
          }
          if (activateGesture(startX, startY, "hold")) {
            replayPendingPoints();
          }
        }, Math.max(0, delay));
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
      if (gestureButton !== 2 && isGestureButtonPressed(gestureButton, event.buttons)) {
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
    """
).strip() + "\n"


OPTIONS_HTML = textwrap.dedent(
    """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>GestHero Options</title>
        <style>
          :root {
            --bg: #f1f3f5;
            --panel: #ffffff;
            --text: #1f2933;
            --muted: #5f6b7a;
            --accent: #2563eb;
            --accent-strong: #1d4ed8;
            --border: #d9dee7;
            --shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
            --radius: 14px;
          }
          * {
            box-sizing: border-box;
          }
          body {
            font-family: "Avenir Next", "Avenir", "Segoe UI", "Helvetica Neue",
              sans-serif;
            margin: 0;
            padding: 24px;
            background: radial-gradient(circle at top, #ffffff, #eef1f5 55%, #e9edf3);
            color: var(--text);
          }
          h1 {
            font-size: 26px;
            margin: 0;
          }
          h2 {
            font-size: 16px;
            margin: 0 0 12px;
          }
          p {
            margin: 0;
          }
          .container {
            max-width: 980px;
            margin: 0 auto;
          }
          .page-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 16px;
            margin-bottom: 18px;
          }
          .subtitle {
            color: var(--muted);
            font-size: 13px;
            margin-top: 6px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            background: var(--panel);
            border-radius: 10px;
            overflow: hidden;
          }
          th,
          td {
            border: 1px solid var(--border);
            padding: 10px;
            text-align: left;
          }
          th {
            background: #f5f7fb;
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
          }
          input[type="text"],
          input[type="number"],
          input[type="color"],
          textarea {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #fff;
            color: var(--text);
            font-size: 14px;
          }
          select {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #fff;
            color: var(--text);
            font-size: 14px;
          }
          input:focus,
          select:focus,
          textarea:focus {
            outline: 2px solid rgba(37, 99, 235, 0.2);
            border-color: var(--accent);
          }
          textarea {
            resize: vertical;
          }
          button {
            padding: 8px 14px;
            border-radius: 9px;
            border: 1px solid transparent;
            background: #e7ebf3;
            color: var(--text);
            font-weight: 600;
            cursor: pointer;
            transition: transform 120ms ease, box-shadow 120ms ease;
          }
          button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
          }
          button.primary {
            background: var(--accent);
            color: #fff;
          }
          button.primary:hover {
            background: var(--accent-strong);
          }
          button.ghost {
            background: #fff;
            border: 1px solid var(--border);
          }
          button.danger {
            background: #fee2e2;
            color: #b91c1c;
          }
          button.danger:hover {
            background: #fecaca;
          }
          .section {
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 16px;
            margin-top: 16px;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
          }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
          }
          .row {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 10px;
          }
          .row label {
            flex: 1;
          }
          .controls {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
          }
          .row-actions button {
            margin: 0;
          }
          #status {
            margin-left: 4px;
            color: var(--accent);
            font-weight: 600;
          }
          .hint {
            font-size: 12px;
            color: var(--muted);
            margin-top: 6px;
          }
          label {
            display: flex;
            flex-direction: column;
            gap: 6px;
            color: var(--muted);
            font-size: 12px;
          }
        </style>
      </head>
      <body>
        <main class="container">
          <header class="page-header">
            <div>
              <h1>GestHero</h1>
              <p class="subtitle">
                U, D, L, R kullan. Bosluk veya virgul ile adim ayir.
              </p>
            </div>
            <p class="hint">Diagonals: UR, UL, DR, DL</p>
          </header>

        <div class="section">
          <h2>Input</h2>
          <div class="grid">
            <label>
              Gesture mouse button
              <select id="mouse-button">
                <option value="right">Right</option>
                <option value="middle">Middle</option>
                <option value="left">Left</option>
              </select>
            </label>
            <label>
              Hold delay (ms)
              <input type="number" id="hold-delay" min="0" step="10" />
            </label>
          </div>
          <p class="hint">
            Right button: short click opens the context menu; hold starts a gesture.
          </p>
        </div>

        <div class="section">
          <h2>Gestures</h2>
          <table>
            <thead>
              <tr>
                <th>Sequence</th>
                <th>Action</th>
                <th>Remove</th>
              </tr>
            </thead>
            <tbody id="gesture-rows"></tbody>
          </table>
          <div class="controls">
            <button id="add-row" class="ghost">Add Gesture</button>
            <button id="save" class="primary">Save</button>
            <span id="status"></span>
          </div>
          <div class="row">
            <label>
              Preset
              <select id="preset-select"></select>
            </label>
            <button id="apply-preset" class="ghost">Apply Preset</button>
          </div>
        </div>

        <div class="section">
          <h2>Behavior</h2>
          <div class="grid">
            <label>
              Min distance (px)
              <input type="number" id="min-distance" min="5" step="1" />
            </label>
            <label>
              Min speed (px/s)
              <input type="number" id="min-speed" min="0" step="50" />
            </label>
            <label>
              Diagonal gestures
              <input type="checkbox" id="diagonal-enabled" />
            </label>
            <label>
              Diagonal bias
              <input type="number" id="diagonal-bias" min="1" step="0.1" />
            </label>
            <label>
              Corner min length (px)
              <input type="number" id="corner-min-length" min="5" step="1" />
            </label>
            <label>
              Corner tolerance (deg)
              <input type="number" id="corner-tolerance" min="0" max="80" step="1" />
            </label>
            <label>
              Show direction overlay
              <input type="checkbox" id="show-direction" />
            </label>
            <label>
              Test mode
              <input type="checkbox" id="test-mode" />
            </label>
          </div>
        </div>

        <div class="section">
          <h2>Visual</h2>
          <div class="grid">
            <label>
              Trail color
              <input type="color" id="trail-color" />
            </label>
            <label>
              Trail width (px)
              <input type="number" id="trail-width" min="1" step="1" />
            </label>
            <label>
              Fade duration (ms)
              <input type="number" id="fade-duration" min="0" step="50" />
            </label>
          </div>
        </div>

        <div class="section">
          <h2>Tabs &amp; Windows</h2>
          <div class="grid">
            <label>
              Zoom step
              <input type="number" id="zoom-step" min="0.05" step="0.05" />
            </label>
          </div>
        </div>

        <div class="section">
          <h2>Search</h2>
          <label>
            Search URL template
            <input type="text" id="search-url" />
          </label>
          <p class="hint">Use %s where the query should go.</p>
        </div>

        <div class="section">
          <h2>Disable on Sites</h2>
          <textarea
            id="disabled-sites"
            rows="4"
            placeholder="example.com"
          ></textarea>
          <p class="hint">One per line or comma separated. Matches subdomains.</p>
        </div>

        <div class="section">
          <h2>Import / Export</h2>
          <div class="row">
            <input
              type="file"
              id="import-file"
              accept=".json,application/json,text/plain"
            />
            <button id="export" class="ghost">Export</button>
          </div>
        </div>

        <div class="section">
          <h2>Debug</h2>
          <label>
            Enable debug logging
            <input type="checkbox" id="debug-log" />
          </label>
          <p class="hint">Debug toggle saves immediately.</p>
          <div class="controls">
            <button id="export-debug" class="ghost">Export Debug Log</button>
            <button id="clear-debug" class="danger">Clear Debug Log</button>
          </div>
        </div>

        <p class="hint">Hold the selected mouse button and drag to draw a gesture.</p>
        <p class="hint">Link actions require starting the gesture on a link.</p>
        <p class="hint">Selection actions require text selected.</p>

        <script src="options.js"></script>
        </main>
      </body>
    </html>
    """
).strip() + "\n"


OPTIONS_JS = textwrap.dedent(
    """
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

    const VALID_TOKENS = new Set(["U", "D", "L", "R", "UR", "UL", "DR", "DL"]);

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
    const debugLogInput = document.getElementById("debug-log");
    const trailColorInput = document.getElementById("trail-color");
    const trailWidthInput = document.getElementById("trail-width");
    const fadeDurationInput = document.getElementById("fade-duration");
    const zoomStepInput = document.getElementById("zoom-step");
    const searchUrlInput = document.getElementById("search-url");
    const disabledSitesInput = document.getElementById("disabled-sites");
    const exportDebugButton = document.getElementById("export-debug");
    const clearDebugButton = document.getElementById("clear-debug");

    function setStatus(text) {
      status.textContent = text;
      setTimeout(() => {
        status.textContent = "";
      }, 1500);
    }

    function tokenizeSequence(value) {
      const raw = String(value || "").trim().toUpperCase();
      if (!raw) {
        return [];
      }
      if (/[\s,>-]/.test(raw)) {
        return raw.split(/[\s,>-]+/).filter(Boolean);
      }
      if (raw.length === 2 && VALID_TOKENS.has(raw)) {
        return [raw];
      }
      return raw.split("");
    }

    function normalizeSequence(sequence) {
      return tokenizeSequence(sequence)
        .map((token) => token.replace(/[^UDLR]/g, ""))
        .filter((token) => VALID_TOKENS.has(token))
        .join(" ");
    }

    function createActionSelect(selected) {
      const select = document.createElement("select");
      ACTIONS.forEach((action) => {
        const option = document.createElement("option");
        option.value = action.value;
        option.textContent = action.label;
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
      seqCell.appendChild(input);

      const actionCell = document.createElement("td");
      const select = createActionSelect(action || ACTIONS[0].value);
      actionCell.appendChild(select);

      const removeCell = document.createElement("td");
      removeCell.className = "row-actions";
      const removeButton = document.createElement("button");
      removeButton.textContent = "Remove";
      removeButton.addEventListener("click", () => row.remove());
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
      mouseButtonSelect.value = settings.mouseButton || DEFAULT_SETTINGS.mouseButton;
      holdDelayInput.value = settings.holdDelayMs;
      minDistanceInput.value = settings.minDistance;
      minSpeedInput.value = settings.minSpeed;
      diagonalEnabledInput.checked = Boolean(settings.diagonalEnabled);
      diagonalBiasInput.value = settings.diagonalBias;
      cornerMinLengthInput.value = settings.cornerMinLength;
      cornerToleranceInput.value = settings.cornerToleranceDeg;
      showDirectionInput.checked = Boolean(settings.showDirection);
      testModeInput.checked = Boolean(settings.testMode);
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
        diagonalBias: Number(diagonalBiasInput.value) || DEFAULT_SETTINGS.diagonalBias,
        cornerMinLength:
          Number(cornerMinLengthInput.value) || DEFAULT_SETTINGS.cornerMinLength,
        cornerToleranceDeg:
          Number(cornerToleranceInput.value) ||
          DEFAULT_SETTINGS.cornerToleranceDeg,
        showDirection: showDirectionInput.checked,
        testMode: testModeInput.checked,
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
        }
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
        setStatus("Saved.");
      });
    }

    function saveSettingsOnly() {
      const settings = collectSettings();
      chrome.storage.sync.set({ settings }, () => {
        setStatus("Settings saved.");
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
      setStatus("Preset loaded.");
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
          link.download = "simple_gestures_settings.json";
          link.click();
          URL.revokeObjectURL(url);
          setStatus("Exported.");
        }
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
            setStatus("Imported.");
          });
        } catch (error) {
          setStatus("Import failed.");
        }
      };
      reader.readAsText(file);
    }

    function exportDebugLog() {
      chrome.runtime.sendMessage({ type: "getDebugLog" }, (response) => {
        if (chrome.runtime.lastError) {
          setStatus("Debug log unavailable.");
          return;
        }
        const events = (response && response.events) || [];
        if (!events.length) {
          setStatus("No events collected yet.");
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
        setStatus("Debug log exported.");
      });
    }

    function clearDebugLog() {
      chrome.runtime.sendMessage({ type: "clearDebugLog" }, () => {
        if (chrome.runtime.lastError) {
          setStatus("Debug log unavailable.");
          return;
        }
        setStatus("Debug log cleared.");
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

    populatePresets();
    loadOptions();
    """
).strip() + "\n"


def write_text(path, content):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_binary(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def render_svg_to_png(svg_path, png_path, size):
    try:
        import cairosvg  # type: ignore

        cairosvg.svg2png(
            url=svg_path,
            write_to=png_path,
            output_width=size,
            output_height=size,
        )
        return True
    except Exception:
        pass

    rsvg_convert = shutil.which("rsvg-convert")
    if rsvg_convert:
        try:
            subprocess.run(
                [
                    rsvg_convert,
                    "-w",
                    str(size),
                    "-h",
                    str(size),
                    "-o",
                    png_path,
                    svg_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    sips = shutil.which("sips")
    if sips:
        try:
            subprocess.run(
                [
                    sips,
                    "-s",
                    "format",
                    "png",
                    "-z",
                    str(size),
                    str(size),
                    svg_path,
                    "--out",
                    png_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    return False


def main():
    root = os.path.join(os.getcwd(), "gestHero")
    os.makedirs(root, exist_ok=True)

    manifest = copy.deepcopy(MANIFEST)
    svg_source = os.path.join(os.getcwd(), "gestHero.svg")
    if os.path.isfile(svg_source):
        svg_target = os.path.join(root, "gestHero.svg")
        with open(svg_source, "rb") as handle:
            write_binary(svg_target, handle.read())
        sizes = [16, 48, 128]
        converted = True
        for size in sizes:
            target = os.path.join(root, f"icon{size}.png")
            if not render_svg_to_png(svg_source, target, size):
                converted = False
                break
        if converted:
            icon_map = {
                "16": "icon16.png",
                "48": "icon48.png",
                "128": "icon128.png",
            }
            manifest["icons"] = icon_map
            manifest["action"]["default_icon"] = icon_map

    if "icons" not in manifest:
        icon_bytes = base64.b64decode(ICON_PNG_BASE64)
        write_binary(os.path.join(root, "icon16.png"), icon_bytes)
        write_binary(os.path.join(root, "icon48.png"), icon_bytes)
        write_binary(os.path.join(root, "icon128.png"), icon_bytes)

    write_json(os.path.join(root, "manifest.json"), manifest)
    write_text(os.path.join(root, "background.js"), BACKGROUND_JS)
    write_text(os.path.join(root, "content.js"), CONTENT_JS)
    write_text(os.path.join(root, "options.html"), OPTIONS_HTML)
    write_text(os.path.join(root, "options.js"), OPTIONS_JS)

    print("Created extension in:", root)


if __name__ == "__main__":
    main()
