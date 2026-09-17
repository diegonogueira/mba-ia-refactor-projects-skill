const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SALT_BYTES = 16;
const KEY_LENGTH = 64;

// Stored format: scrypt$<salt hex>$<derived key hex>
async function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derivedKey = await scrypt(password, salt, KEY_LENGTH);
    return `scrypt$${salt}$${derivedKey.toString('hex')}`;
}

module.exports = { hashPassword };
