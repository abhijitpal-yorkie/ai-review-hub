const PREFIX_STYLES = {
  info: "color:#0fa47f;font-weight:600",
  warn: "color:#b7791f;font-weight:600",
  error: "color:#c0392b;font-weight:600",
  debug: "color:#7a7a7a",
};

function log(level, msg, ...args) {
  const ts = new Date().toTimeString().slice(0, 8);
  const style = PREFIX_STYLES[level] || "";
  // eslint-disable-next-line no-console
  console.log(`%c[${ts}] ${level.toUpperCase()}`, style, msg, ...args);
}

export const logger = {
  info: (m, ...a) => log("info", m, ...a),
  warn: (m, ...a) => log("warn", m, ...a),
  error: (m, ...a) => log("error", m, ...a),
  debug: (m, ...a) => log("debug", m, ...a),
};
