const DEFAULT_PORT = 3000;
const DEFAULT_HOST = '127.0.0.1';
const DEFAULT_DATABASE_PATH = ':memory:';
const DEFAULT_LOG_LEVEL = 'info';
const MAX_PORT = 65535;

function parsePort(value) {
    if (value === undefined || value === '') return DEFAULT_PORT;
    const port = Number(value);
    if (!Number.isInteger(port) || port < 0 || port > MAX_PORT) {
        throw new Error(`PORT inválida: ${value}`);
    }
    return port;
}

function loadSettings(env = process.env) {
    return Object.freeze({
        port: parsePort(env.PORT),
        host: env.HOST || DEFAULT_HOST,
        databasePath: env.DATABASE_PATH || DEFAULT_DATABASE_PATH,
        adminToken: env.ADMIN_TOKEN || null,
        logLevel: env.LOG_LEVEL || DEFAULT_LOG_LEVEL,
    });
}

module.exports = { loadSettings };
