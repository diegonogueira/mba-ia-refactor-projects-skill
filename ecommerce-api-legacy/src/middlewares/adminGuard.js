const crypto = require('crypto');
const { ForbiddenError } = require('../utils/errors');

const ADMIN_TOKEN_HEADER = 'X-Admin-Token';
const DISABLED_MESSAGE = 'Rotas administrativas desabilitadas';

const digest = (value) => crypto.createHash('sha256').update(value).digest();

// Compares fixed-length digests so neither the content nor the length of the token leaks through timing.
const tokensMatch = (received, expected) => crypto.timingSafeEqual(digest(received), digest(expected));

// Closed by default: the admin routes only open when ADMIN_ENDPOINTS_ENABLED and ADMIN_TOKEN are both set.
function createAdminGuard({ adminToken, adminEndpointsEnabled }) {
    return (req, res, next) => {
        if (!adminEndpointsEnabled || !adminToken) return next(new ForbiddenError(DISABLED_MESSAGE));
        if (tokensMatch(req.get(ADMIN_TOKEN_HEADER) || '', adminToken)) return next();
        return next(new ForbiddenError());
    };
}

module.exports = { createAdminGuard };
