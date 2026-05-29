const js = require("@eslint/js");

const browserGlobals = {
  window: "readonly",
  document: "readonly",
  history: "readonly",
  navigator: "readonly",
  performance: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  MouseEvent: "readonly",
  Blob: "readonly",
  URL: "readonly",
  FileReader: "readonly",
  Set: "readonly",
  Map: "readonly",
  chrome: "readonly",
  console: "readonly",
};

module.exports = [
  {
    ignores: ["node_modules/**", "gestHero.zip"],
  },
  js.configs.recommended,
  {
    // Extension scripts run as classic scripts in the browser / SW context.
    files: ["gestHero/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...browserGlobals,
        // gestures-core.js exposes a global and an optional CommonJS export.
        GestureCore: "readonly",
        module: "writable",
        self: "readonly",
        globalThis: "readonly",
      },
    },
  },
  {
    // Node test files and tooling config.
    files: ["tests/**/*.js", "eslint.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "commonjs",
      globals: {
        require: "readonly",
        module: "writable",
        __dirname: "readonly",
        process: "readonly",
        console: "readonly",
      },
    },
  },
];
