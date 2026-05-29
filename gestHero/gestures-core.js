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
  function getDirection(dx, dy, opts) {
    var options = opts || {};
    var absX = Math.abs(dx);
    var absY = Math.abs(dy);
    if (absX === 0 && absY === 0) {
      return null;
    }
    if (!options.diagonalEnabled) {
      return absX >= absY ? (dx > 0 ? "R" : "L") : dy > 0 ? "D" : "U";
    }
    var bias = Math.max(1, Number(options.diagonalBias) || 1);
    var tolerance = Math.max(0, Number(options.cornerToleranceDeg) || 0);
    if (absY === 0) {
      return dx > 0 ? "R" : "L";
    }
    if (absX === 0) {
      return dy > 0 ? "D" : "U";
    }
    var angle = (Math.atan2(absY, absX) * 180) / Math.PI;
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

  var api = {
    VALID_TOKENS: VALID_TOKENS,
    tokenizeSequence: tokenizeSequence,
    sanitizeTokens: sanitizeTokens,
    collapseRepeats: collapseRepeats,
    simplifyTokens: simplifyTokens,
    formatSequence: formatSequence,
    getDirection: getDirection,
    getAxisDistance: getAxisDistance,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  // Expose as a global so the content script / options page can use it.
  root.GestureCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
