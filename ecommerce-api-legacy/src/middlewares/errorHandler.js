const { AppError } = require('../utils/errors');

const BODY_PARSE_FAILED = 'entity.parse.failed';

// Error bodies stay plain text, as in the original API.
function makeErrorHandler({ logger }) {
    return (err, req, res, next) => {
        if (res.headersSent) return next(err);

        if (err instanceof AppError) return res.status(err.statusCode).send(err.message);
        if (err.type === BODY_PARSE_FAILED) return res.status(400).send('Bad Request');
        if (err.expose && err.status >= 400 && err.status < 500) return res.status(err.status).send(err.message);

        logger.error(`${req.method} ${req.originalUrl} falhou:`, err);
        return res.status(500).send('Erro interno do servidor');
    };
}

module.exports = { makeErrorHandler };
