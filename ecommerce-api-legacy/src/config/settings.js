const DEFAULT_PORT = 3000;
const DEFAULT_HOST = '127.0.0.1';
const DEFAULT_DATABASE_PATH = ':memory:';
const DEFAULT_LOG_LEVEL = 'info';
const MAX_PORT = 65535;
const TRUTHY_VALUES = Object.freeze(['1', 'true', 'yes', 'on']);

function parsePort(value) {
    if (value === undefined || value === '') return DEFAULT_PORT;
    const port = Number(value);
    if (!Number.isInteger(port) || port < 0 || port > MAX_PORT) {
        throw new Error(`PORT inválida: ${value}`);
    }
    return port;
}

const parseBoolean = (value) => TRUTHY_VALUES.includes(String(value ?? '').trim().toLowerCase());

function loadSettings(env = process.env) {
    return Object.freeze({
        port: parsePort(env.PORT),
        host: env.HOST || DEFAULT_HOST,
        databasePath: env.DATABASE_PATH || DEFAULT_DATABASE_PATH,
        // Admin routes are closed unless both the flag and the token are configured.
        adminEndpointsEnabled: parseBoolean(env.ADMIN_ENDPOINTS_ENABLED),
        adminToken: env.ADMIN_TOKEN || null,
        // No credential default: when unset the seed account gets a random password.
        seedUserPassword: env.SEED_USER_PASSWORD || null,
        logLevel: env.LOG_LEVEL || DEFAULT_LOG_LEVEL,
    });
}

module.exports = { loadSettings };
