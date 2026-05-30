const { test } = require("node:test");
const assert = require("node:assert/strict");

const core = require("../gestHero/gestures-core.js");

test("tokenizeSequence splits on whitespace and separators", () => {
  assert.deepEqual(core.tokenizeSequence("U R"), ["U", "R"]);
  assert.deepEqual(core.tokenizeSequence("u>r"), ["U", "R"]);
  assert.deepEqual(core.tokenizeSequence("D,L"), ["D", "L"]);
  assert.deepEqual(core.tokenizeSequence(""), []);
});

test("tokenizeSequence keeps a lone two-letter diagonal token", () => {
  assert.deepEqual(core.tokenizeSequence("UR"), ["UR"]);
  assert.deepEqual(core.tokenizeSequence("ur"), ["UR"]);
});

test("tokenizeSequence splits packed single-letter input", () => {
  assert.deepEqual(core.tokenizeSequence("UDLR"), ["U", "D", "L", "R"]);
});

test("sanitizeTokens drops invalid characters and tokens", () => {
  assert.deepEqual(core.sanitizeTokens("U X R"), ["U", "R"]);
  assert.deepEqual(core.sanitizeTokens("UR"), ["UR"]);
  assert.deepEqual(core.sanitizeTokens("123"), []);
});

test("collapseRepeats removes consecutive duplicates only", () => {
  assert.deepEqual(core.collapseRepeats(["U", "U", "R", "R"]), ["U", "R"]);
  assert.deepEqual(core.collapseRepeats(["U", "R", "U"]), ["U", "R", "U"]);
  assert.deepEqual(core.collapseRepeats([]), []);
});

test("simplifyTokens folds diagonals between matching cardinals", () => {
  // U UR R -> U R (the corner-smoothing case from the dev journal)
  assert.deepEqual(core.simplifyTokens(["U", "UR", "R"]), ["U", "R"]);
});

test("simplifyTokens reduces a trailing diagonal after a matching cardinal", () => {
  assert.deepEqual(core.simplifyTokens(["U", "UR"]), ["U", "R"]);
});

test("simplifyTokens leaves standalone diagonals intact", () => {
  assert.deepEqual(core.simplifyTokens(["UR"]), ["UR"]);
  assert.deepEqual(core.simplifyTokens(["L", "DR"]), ["L", "DR"]);
});

test("formatSequence joins tokens with single spaces", () => {
  assert.equal(core.formatSequence(["U", "R"]), "U R");
  assert.equal(core.formatSequence([]), "");
});

test("getDirection returns null for no movement", () => {
  assert.equal(core.getDirection(0, 0, { diagonalEnabled: true }), null);
});

test("getDirection resolves pure cardinals", () => {
  const opts = {
    diagonalEnabled: true,
    diagonalBias: 1.4,
    cornerToleranceDeg: 35,
  };
  assert.equal(core.getDirection(10, 0, opts), "R");
  assert.equal(core.getDirection(-10, 0, opts), "L");
  assert.equal(core.getDirection(0, 10, opts), "D");
  assert.equal(core.getDirection(0, -10, opts), "U");
});

test("getDirection resolves diagonals at 45 degrees", () => {
  const opts = {
    diagonalEnabled: true,
    diagonalBias: 1.4,
    cornerToleranceDeg: 35,
  };
  assert.equal(core.getDirection(10, 10, opts), "DR");
  assert.equal(core.getDirection(10, -10, opts), "UR");
  assert.equal(core.getDirection(-10, 10, opts), "DL");
  assert.equal(core.getDirection(-10, -10, opts), "UL");
});

test("getDirection collapses to cardinals when diagonals disabled", () => {
  const opts = { diagonalEnabled: false };
  assert.equal(core.getDirection(10, 3, opts), "R");
  assert.equal(core.getDirection(3, 10, opts), "D");
});

test("getDirection honours the corner tolerance angle", () => {
  // Shallow angle (< tolerance) should read as horizontal.
  const opts = {
    diagonalEnabled: true,
    diagonalBias: 1.4,
    cornerToleranceDeg: 35,
  };
  assert.equal(core.getDirection(100, 10, opts), "R");
});

test("getAxisDistance picks the dominant axis", () => {
  assert.equal(core.getAxisDistance("R", 10, 3), 10);
  assert.equal(core.getAxisDistance("U", 3, 10), 10);
  assert.equal(core.getAxisDistance("DR", 10, 4), 4);
  assert.equal(core.getAxisDistance(null, 10, 4), 0);
});

test("getDirection diagonal band boundaries (default tolerance 35, bias 1.4)", () => {
  const opts = {
    diagonalEnabled: true,
    diagonalBias: 1.4,
    cornerToleranceDeg: 35,
  };
  // Just inside the tolerance cone (~30 deg) -> cardinal.
  assert.equal(core.getDirection(100, 57, opts), "R"); // ~29.7 deg
  // Solidly in the diagonal band (45 deg) -> diagonal.
  assert.equal(core.getDirection(100, 100, opts), "DR");
  // Just inside the vertical cone (~60 deg) -> cardinal.
  assert.equal(core.getDirection(57, 100, opts), "D"); // ~60.3 deg
});

test("normalizeForMatch collapses repeats into the lookup key", () => {
  assert.equal(core.normalizeForMatch("U U R"), "U R");
  assert.equal(core.normalizeForMatch("u>u>r"), "U R");
  assert.equal(core.normalizeForMatch("UR"), "UR");
  assert.equal(core.normalizeForMatch("XY"), "");
});

test("findConflicts flags sequences that map to the same key", () => {
  const conflicts = core.findConflicts([
    { sequence: "U R", action: "new_tab" },
    { sequence: "U U R", action: "close_tab" },
    { sequence: "L", action: "go_back" },
  ]);
  assert.equal(conflicts.length, 1);
  assert.equal(conflicts[0].sequence, "U R");
  assert.deepEqual(conflicts[0].actions.sort(), ["close_tab", "new_tab"]);
});

test("findConflicts returns nothing for unique gestures", () => {
  assert.deepEqual(
    core.findConflicts([
      { sequence: "L", action: "go_back" },
      { sequence: "R", action: "go_forward" },
    ]),
    [],
  );
});

test("recognizePoints reads a straight drag as one cardinal", () => {
  const tokens = core.recognizePoints(
    [
      { x: 0, y: 0 },
      { x: 30, y: 0 },
    ],
    { diagonalEnabled: true, minDistance: 20, cornerMinLength: 18 },
  );
  assert.deepEqual(tokens, ["R"]);
});

test("recognizePoints reads an L-shape as two tokens", () => {
  const tokens = core.recognizePoints(
    [
      { x: 0, y: 0 },
      { x: 0, y: 30 },
      { x: 30, y: 30 },
    ],
    { diagonalEnabled: true, minDistance: 20, cornerMinLength: 18 },
  );
  assert.deepEqual(tokens, ["D", "R"]);
});

test("recognizePoints ignores movement below the min distance", () => {
  const tokens = core.recognizePoints(
    [
      { x: 0, y: 0 },
      { x: 5, y: 0 },
    ],
    { diagonalEnabled: true, minDistance: 20, cornerMinLength: 18 },
  );
  assert.deepEqual(tokens, []);
});

const RECOG_OPTS = {
  diagonalEnabled: true,
  diagonalBias: 1.4,
  cornerToleranceDeg: 35,
  minDistance: 20,
  cornerMinLength: 18,
};

// Build evenly spaced points from `from` to `to` (inclusive of the end).
function segment(from, to, step) {
  const dx = Math.sign(to.x - from.x);
  const dy = Math.sign(to.y - from.y);
  const out = [];
  let x = from.x;
  let y = from.y;
  while (x !== to.x || y !== to.y) {
    x += dx * Math.min(step, Math.abs(to.x - x));
    y += dy * Math.min(step, Math.abs(to.y - y));
    out.push({ x, y });
  }
  return out;
}

test("recognizePoints detects a tall, thin L corner (regression)", () => {
  // Long down leg then a short right leg: the corner must still register.
  const points = [{ x: 0, y: 0 }]
    .concat(segment({ x: 0, y: 0 }, { x: 0, y: 300 }, 10))
    .concat(segment({ x: 0, y: 300 }, { x: 80, y: 300 }, 10));
  assert.deepEqual(core.recognizePoints(points, RECOG_OPTS), ["D", "R"]);
});

test("recognizePoints keeps a long straight line as a single token", () => {
  const points = [{ x: 0, y: 0 }].concat(
    segment({ x: 0, y: 0 }, { x: 400, y: 0 }, 8),
  );
  assert.deepEqual(core.recognizePoints(points, RECOG_OPTS), ["R"]);
});

test("recognizePoints handles a three-leg square bracket (D R U)", () => {
  const points = [{ x: 0, y: 0 }]
    .concat(segment({ x: 0, y: 0 }, { x: 0, y: 120 }, 10))
    .concat(segment({ x: 0, y: 120 }, { x: 120, y: 120 }, 10))
    .concat(segment({ x: 120, y: 120 }, { x: 120, y: 0 }, 10));
  assert.deepEqual(core.recognizePoints(points, RECOG_OPTS), ["D", "R", "U"]);
});
