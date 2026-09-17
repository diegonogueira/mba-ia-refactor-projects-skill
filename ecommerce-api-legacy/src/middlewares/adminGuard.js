const crypto = require('crypto');
const { ForbiddenError } = require('../utils/errors');

const ADMIN_TOKEN_HEADER = 'X-Admin-Token';

const digest = (value) => crypto.createHash('sha256').update(value).digest();

// Compares fixed-length digests so neither the content nor the length of the token leaks through timing.
const tokensMatch = (received, expected) => crypto.timingSafeEqual(digest(received), digest(expected));

// Without ADMIN_TOKEN the admin routes stay public, as in the original contract.
function createAdminGuard({ adminToken }) {
    if (!adminToken) return (req, res, next) => next();

    return (req, res, next) => {
        if (tokensMatch(req.get(ADMIN_TOKEN_HEADER) || '', adminToken)) return next();
        return next(new ForbiddenError());
    };
}

module.exports = { createAdminGuard };
