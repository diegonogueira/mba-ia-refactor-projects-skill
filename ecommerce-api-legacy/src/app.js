const { loadSettings } = require('./config/settings');
const { createApp } = require('./createApp');
const { openDatabase } = require('./models/database');
const { initializeDatabase } = require('./models/schema');
const { createLogger } = require('./utils/logger');

async function main() {
    const settings = loadSettings();
    const logger = createLogger(settings.logLevel);

    const db = openDatabase(settings.databasePath);
    await initializeDatabase(db);

    createApp({ db, settings, logger }).listen(settings.port, () => {
        logger.info(`LMS API rodando na porta ${settings.port}`);
    });
}

main().catch((err) => {
    console.error('Falha ao iniciar a aplicação:', err);
    process.exit(1);
});
