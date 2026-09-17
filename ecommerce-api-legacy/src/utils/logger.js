const LEVELS = Object.freeze({ error: 0, warn: 1, info: 2, debug: 3 });

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;

    const write = (name, output) => (message, ...details) => {
        if (LEVELS[name] > threshold) return;
        output(`${new Date().toISOString()} [${name.toUpperCase()}] ${message}`, ...details);
    };

    return Object.freeze({
        error: write('error', console.error),
        warn: write('warn', console.warn),
        info: write('info', console.log),
        debug: write('debug', console.log),
    });
}

module.exports = { createLogger };
