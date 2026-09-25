const { ValidationError } = require('./errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_NUMBER_PATTERN = /^\d+(?:[ -]?\d+)*$/;
const CARD_SEPARATORS = /[ -]/g;
const CARD_DIGITS = Object.freeze({ min: 13, max: 19 });
const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/;

const isFilledString = (value) => typeof value === 'string' && value.trim() !== '';

function parsePositiveInteger(value) {
    if (Number.isInteger(value) && value > 0) return value;
    if (typeof value === 'string' && POSITIVE_INTEGER_PATTERN.test(value)) return Number(value);
    return null;
}

// Card numbers have 13 to 19 digits; spaces and hyphens between groups are accepted and removed.
function parseCardNumber(value) {
    if (typeof value !== 'string' || !CARD_NUMBER_PATTERN.test(value)) return null;
    const digits = value.replace(CARD_SEPARATORS, '');
    return digits.length >= CARD_DIGITS.min && digits.length <= CARD_DIGITS.max ? digits : null;
}

// Request field names (usr, eml, pwd, c_id, card) are part of the public contract.
// courseId is null when c_id cannot identify a course; the checkout answers that as "course not found".
// E-mails are compared case-insensitively, so they are trimmed and lower-cased before reaching the models.
function validateCheckoutInput(body) {
    const { usr: rawName, eml: rawEmail, pwd: password, c_id: rawCourseId, card: rawCardNumber } = body || {};
    if (!rawName || !rawEmail || !rawCourseId || !rawCardNumber) throw new ValidationError();
    if (!isFilledString(rawName) || typeof rawEmail !== 'string') throw new ValidationError();

    const email = rawEmail.trim().toLowerCase();
    const cardNumber = parseCardNumber(rawCardNumber);
    const validPassword = password === undefined || password === null || typeof password === 'string';
    if (!EMAIL_PATTERN.test(email) || cardNumber === null || !validPassword) throw new ValidationError();

    return {
        name: rawName.trim(),
        email,
        password: password || null,
        courseId: parsePositiveInteger(rawCourseId),
        cardNumber,
    };
}

// Route ids are positive integers; anything else is a bad request instead of a no-op reported as success.
function validateUserId(rawUserId) {
    const userId = parsePositiveInteger(rawUserId);
    if (userId === null) throw new ValidationError();
    return userId;
}

module.exports = { validateCheckoutInput, validateUserId };
