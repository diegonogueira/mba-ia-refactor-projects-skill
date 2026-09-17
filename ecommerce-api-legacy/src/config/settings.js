const DEFAULT_PORT = 3000;
const DEFAULT_DATABASE_PATH = ':memory:';
const DEFAULT_LOG_LEVEL = 'info';

function loadSettings(env = process.env) {
    return Object.freeze({
        port: Number(env.PORT) || DEFAULT_PORT,
        databasePath: env.DATABASE_PATH || DEFAULT_DATABASE_PATH,
        paymentGatewayKey: env.PAYMENT_GATEWAY_KEY || null,
        adminToken: env.ADMIN_TOKEN || null,
        logLevel: env.LOG_LEVEL || DEFAULT_LOG_LEVEL,
    });
}

module.exports = { loadSettings };
