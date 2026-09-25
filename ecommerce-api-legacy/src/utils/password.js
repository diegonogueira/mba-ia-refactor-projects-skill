const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SCHEME = 'scrypt';
const SALT_BYTES = 16;
const KEY_LENGTH = 64;
// OWASP-recommended scrypt cost; maxmem has to fit 128 * N * r bytes, above Node's 32 MB default.
const COST = Object.freeze({ N: 131072, r: 8, p: 1 });
const MAXMEM_HEADROOM = 1.5;

const scryptOptions = ({ N, r, p }) => ({ N, r, p, maxmem: Math.ceil(128 * N * r * MAXMEM_HEADROOM) });

// Stored format: scrypt$<N>$<r>$<p>$<salt hex>$<derived key hex> — the cost travels with the hash,
// so raising it later does not make the existing hashes unverifiable.
async function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derivedKey = await scrypt(password, salt, KEY_LENGTH, scryptOptions(COST));
    return `${SCHEME}$${COST.N}$${COST.r}$${COST.p}$${salt}$${derivedKey.toString('hex')}`;
}

// False for a missing or malformed hash, so accounts stored without a credential never authenticate.
async function verifyPassword(password, stored) {
    const [scheme, N, r, p, salt, keyHex] = String(stored ?? '').split('$');
    const cost = { N: Number(N), r: Number(r), p: Number(p) };
    const expected = Buffer.from(keyHex ?? '', 'hex');
    if (scheme !== SCHEME || !salt || expected.length !== KEY_LENGTH || !Object.values(cost).every(Number.isInteger)) {
        return false;
    }

    const candidate = await scrypt(password, salt, KEY_LENGTH, scryptOptions(cost));
    return crypto.timingSafeEqual(candidate, expected);
}

module.exports = { hashPassword, verifyPassword };
