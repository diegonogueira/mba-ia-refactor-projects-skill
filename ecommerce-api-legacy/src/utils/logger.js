const LEVELS = Object.freeze({ error: 0, warn: 1, info: 2, debug: 3 });

const WRITERS = Object.freeze({
    error: console.error,
    warn: console.warn,
    info: console.log,
    debug: console.log,
});

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;

    const logger = {};
    for (const [name, severity] of Object.entries(LEVELS)) {
        logger[name] = (...args) => {
            if (severity <= threshold) {
                WRITERS[name](`[${new Date().toISOString()}] ${name.toUpperCase()}`, ...args);
            }
        };
    }
    return Object.freeze(logger);
}

module.exports = { createLogger };
