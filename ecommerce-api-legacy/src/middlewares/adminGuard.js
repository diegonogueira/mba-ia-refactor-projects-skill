const crypto = require('crypto');
const { ForbiddenError } = require('../utils/errors');

const ADMIN_TOKEN_HEADER = 'X-Admin-Token';

// Opt-in guard: without ADMIN_TOKEN the routes stay public (original contract);
// with it, requests must send a matching X-Admin-Token header.
function makeAdminGuard({ adminToken }) {
    if (!adminToken) return (req, res, next) => next();

    const expected = Buffer.from(adminToken);
    return (req, res, next) => {
        const provided = Buffer.from(req.get(ADMIN_TOKEN_HEADER) || '');
        const authorized = provided.length === expected.length && crypto.timingSafeEqual(provided, expected);
        return authorized ? next() : next(new ForbiddenError());
    };
}

module.exports = { makeAdminGuard };
