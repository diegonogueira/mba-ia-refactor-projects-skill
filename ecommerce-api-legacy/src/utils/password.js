const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);

const HASH_SCHEME = 'scrypt';
const SALT_BYTES = 16;
const KEY_LENGTH = 64;
const RANDOM_PASSWORD_BYTES = 24;

async function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derivedKey = await scrypt(password, salt, KEY_LENGTH);
    return `${HASH_SCHEME}$${salt}$${derivedKey.toString('hex')}`;
}

// Used when the client omits the password: the account gets an unguessable secret
// instead of a well-known default.
function generateRandomPassword() {
    return crypto.randomBytes(RANDOM_PASSWORD_BYTES).toString('base64url');
}

module.exports = { hashPassword, generateRandomPassword };
