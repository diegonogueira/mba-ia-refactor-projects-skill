const { AppError } = require('../utils/errors');

const notFoundHandler = (req, res) => res.status(404).send('Not Found');

// Error bodies stay plain text, as in the original API.
function createErrorHandler({ logger }) {
    // Express recognizes error middlewares by their four parameters.
    // eslint-disable-next-line no-unused-vars
    return (err, req, res, next) => {
        if (res.headersSent) return next(err);
        if (err instanceof AppError) return res.status(err.statusCode).send(err.message);
        if (err.type === 'entity.parse.failed') return res.status(400).send('Bad Request');
        if (err.expose && err.statusCode >= 400 && err.statusCode < 500) {
            return res.status(err.statusCode).send(err.message);
        }

        logger.error(`Erro inesperado em ${req.method} ${req.originalUrl}`, err);
        return res.status(500).send('Erro interno do servidor');
    };
}

module.exports = { notFoundHandler, createErrorHandler };
