const { loadSettings } = require('./config/settings');
const { createLogger } = require('./utils/logger');
const { openDatabase } = require('./models/database');
const { initSchema, seedDatabase } = require('./models/schema');
const createApp = require('./createApp');

async function main() {
    const settings = loadSettings();
    const logger = createLogger(settings.logLevel);

    const db = await openDatabase(settings.databasePath);
    await initSchema(db);
    await seedDatabase(db, { userPassword: settings.seedUserPassword });

    if (!settings.adminEndpointsEnabled || !settings.adminToken) {
        logger.warn('Rotas administrativas fechadas (403): defina ADMIN_ENDPOINTS_ENABLED=true e ADMIN_TOKEN para habilitá-las.');
    }

    const server = createApp({ db, settings, logger }).listen(settings.port, settings.host, () => {
        logger.info(`LMS API rodando em http://${settings.host}:${settings.port}`);
    });
    server.on('error', (err) => {
        logger.error('Falha no servidor HTTP', err);
        process.exit(1);
    });

    // Stops accepting requests, lets the in-flight ones finish and only then closes the database.
    const shutdown = (signal) => {
        logger.info(`${signal} recebido, encerrando`);
        server.close(() => db.close().then(() => process.exit(0), (err) => {
            logger.error('Falha ao fechar o banco', err);
            process.exit(1);
        }));
    };
    process.once('SIGTERM', shutdown);
    process.once('SIGINT', shutdown);
}

main().catch((err) => {
    console.error('Falha ao iniciar a aplicação', err);
    process.exit(1);
});
