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
    await seedDatabase(db);

    if (!settings.adminToken) {
        logger.warn('ADMIN_TOKEN não definido: as rotas administrativas continuam públicas.');
    }

    const server = createApp({ db, settings, logger }).listen(settings.port, settings.host, () => {
        logger.info(`LMS API rodando em http://${settings.host}:${settings.port}`);
    });
    server.on('error', (err) => {
        logger.error('Falha no servidor HTTP', err);
        process.exit(1);
    });
}

main().catch((err) => {
    console.error('Falha ao iniciar a aplicação', err);
    process.exit(1);
});
