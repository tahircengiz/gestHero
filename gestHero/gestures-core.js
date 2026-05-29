// gestures-core.js
// Shared, side-effect-free gesture helpers used by both the content script and
// the options page. Also exported as a CommonJS module so the unit tests can
// import the exact same logic that ships in the extension.
//
// IMPORTANT: keep this file free of DOM/chrome APIs and module-level state so it
// stays trivially testable and behaves identically in every context.
(function (root) {
  "use strict";

  var VALID_TOKENS = new Set(["U", "D", "L", "R", "UR", "UL", "DR", "DL"]);

  function tokenizeSequence(value) {
    var raw = String(value || "")
      .trim()
      .toUpperCase();
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

  // Strips invalid characters and keeps only recognised direction tokens.
  // Returns an array (callers decide whether to collapse repeats / join).
  function sanitizeTokens(value) {
    return tokenizeSequence(value)
      .map(function (token) {
        return token.replace(/[^UDLR]/g, "");
      })
      .filter(function (token) {
        return VALID_TOKENS.has(token);
      });
  }

  function collapseRepeats(tokens) {
    var result = [];
    var last = null;
    (tokens || []).forEach(function (token) {
      if (token && token !== last) {
        result.push(token);
        last = token;
      }
    });
    return result;
  }

  function simplifyTokens(tokens) {
    var collapsed = collapseRepeats(tokens);
    var result = [];
    for (var i = 0; i < collapsed.length; i += 1) {
      var token = collapsed[i];
      if (!token || token.length !== 2) {
        result.push(token);
        continue;
      }
      var prev = result[result.length - 1];
      var next = collapsed[i + 1];
      var prevCardinal = prev && prev.length === 1;
      var nextCardinal = next && next.length === 1;
      var matchesPrev = prevCardinal && token.includes(prev);
      var matchesNext = nextCardinal && token.includes(next);
      if (matchesPrev && matchesNext) {
        continue;
      }
      if (matchesPrev && !nextCardinal) {
        var replacement = token.replace(prev, "");
        if (replacement.length === 1) {
          result.push(replacement);
          continue;
        }
      }
      result.push(token);
    }
    return result;
  }

  function formatSequence(tokens) {
    return (tokens || []).join(" ");
  }

  // Resolve the gesture direction for a movement delta.
  // `opts` carries the relevant settings (diagonalEnabled / diagonalBias /
  // cornerToleranceDeg) so this function stays pure and testable.
  //
  // Model: the movement angle (0..90 deg from the horizontal axis) decides the
  // direction. A tolerance cone around each axis snaps to a cardinal; the
  // diagonal band in between yields a diagonal unless a strong axis `bias`
  // still pulls it back to a cardinal. The `bias` knob is intentionally kept
  // for backwards compatibility with saved settings.
  function getDirection(dx, dy, opts) {
    var options = opts || {};
    var absX = Math.abs(dx);
    var absY = Math.abs(dy);
    if (absX === 0 && absY === 0) {
      return null;
    }
    var horizontal = dx > 0 ? "R" : "L";
    var vertical = dy > 0 ? "D" : "U";
    if (!options.diagonalEnabled) {
      return absX >= absY ? horizontal : vertical;
    }
    if (absY === 0) {
      return horizontal;
    }
    if (absX === 0) {
      return vertical;
    }
    var angle = (Math.atan2(absY, absX) * 180) / Math.PI;
    var tolerance = Math.max(0, Number(options.cornerToleranceDeg) || 0);
    if (angle <= tolerance) {
      return horizontal;
    }
    if (angle >= 90 - tolerance) {
      return vertical;
    }
    var bias = Math.max(1, Number(options.diagonalBias) || 1);
    if (absX >= absY * bias) {
      return horizontal;
    }
    if (absY >= absX * bias) {
      return vertical;
    }
    if (dx > 0) {
      return dy > 0 ? "DR" : "UR";
    }
    return dy > 0 ? "DL" : "UL";
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

  // Canonical lookup key for matching a gesture: sanitised + repeats collapsed
  // (e.g. "U U R" and "u>u>r" both become "U R"). The content script uses this
  // to build its gesture map, so conflict detection must use the same key.
  function normalizeForMatch(value) {
    return collapseRepeats(sanitizeTokens(value)).join(" ");
  }

  // Detect gesture rows whose canonical sequence collides (the later one would
  // silently win in the lookup map). Returns [{ sequence, actions: [...] }].
  function findConflicts(gestures) {
    var byKey = new Map();
    (gestures || []).forEach(function (item) {
      if (!item) {
        return;
      }
      var key = normalizeForMatch(item.sequence);
      if (!key) {
        return;
      }
      if (!byKey.has(key)) {
        byKey.set(key, []);
      }
      byKey.get(key).push(item.action);
    });
    var conflicts = [];
    byKey.forEach(function (actions, key) {
      if (actions.length > 1) {
        conflicts.push({ sequence: key, actions: actions });
      }
    });
    return conflicts;
  }

  // Stateless recogniser turning a stream of {x, y} points into a simplified
  // token sequence. Shared by the options "draw to record" tool; it mirrors the
  // content script's segment-commit thresholds (without live speed gating).
  function recognizePoints(points, opts) {
    var options = opts || {};
    var pts = points || [];
    if (pts.length < 2) {
      return [];
    }
    var minDistance = Number(options.minDistance) || 20;
    var cornerMinLength = Number(options.cornerMinLength) || 18;
    var directions = [];
    var segStartX = pts[0].x;
    var segStartY = pts[0].y;
    for (var i = 1; i < pts.length; i += 1) {
      var dx = pts[i].x - segStartX;
      var dy = pts[i].y - segStartY;
      var direction = getDirection(dx, dy, options);
      if (!direction) {
        continue;
      }
      var last = directions[directions.length - 1];
      var axisDistance = getAxisDistance(direction, Math.abs(dx), Math.abs(dy));
      var committed = false;
      if (!last) {
        if (axisDistance >= minDistance) {
          directions.push(direction);
          committed = true;
        }
      } else if (direction !== last && axisDistance >= cornerMinLength) {
        directions.push(direction);
        committed = true;
      }
      if (committed) {
        segStartX = pts[i].x;
        segStartY = pts[i].y;
      }
    }
    return simplifyTokens(directions);
  }

  var api = {
    VALID_TOKENS: VALID_TOKENS,
    tokenizeSequence: tokenizeSequence,
    sanitizeTokens: sanitizeTokens,
    collapseRepeats: collapseRepeats,
    simplifyTokens: simplifyTokens,
    formatSequence: formatSequence,
    getDirection: getDirection,
    getAxisDistance: getAxisDistance,
    normalizeForMatch: normalizeForMatch,
    findConflicts: findConflicts,
    recognizePoints: recognizePoints,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  // Expose as a global so the content script / options page can use it.
  root.GestureCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
