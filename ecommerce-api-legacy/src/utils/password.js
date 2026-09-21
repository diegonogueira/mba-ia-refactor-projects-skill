const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SALT_BYTES = 16;
const KEY_LENGTH = 64;
// OWASP-recommended scrypt cost; maxmem has to fit 128 * N * r bytes, above Node's 32 MB default.
const COST = Object.freeze({ N: 131072, r: 8, p: 1 });
const SCRYPT_OPTIONS = Object.freeze({ ...COST, maxmem: 192 * 1024 * 1024 });

// Stored format: scrypt$<N>$<r>$<p>$<salt hex>$<derived key hex> — the cost travels with the hash,
// so raising it later does not make the existing hashes unverifiable.
async function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derivedKey = await scrypt(password, salt, KEY_LENGTH, SCRYPT_OPTIONS);
    return `scrypt$${COST.N}$${COST.r}$${COST.p}$${salt}$${derivedKey.toString('hex')}`;
}

module.exports = { hashPassword };
