const { ValidationError } = require('./errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_NUMBER_PATTERN = /^\d+(?:[ -]?\d+)*$/;
const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/;

const isFilledString = (value) => typeof value === 'string' && value.trim() !== '';

function parsePositiveInteger(value) {
    if (Number.isInteger(value) && value > 0) return value;
    if (typeof value === 'string' && POSITIVE_INTEGER_PATTERN.test(value)) return Number(value);
    return null;
}

// Request field names (usr, eml, pwd, c_id, card) are part of the public contract.
// courseId is null when c_id cannot identify a course; the checkout answers that as "course not found".
function validateCheckoutInput(body) {
    const { usr: name, eml: email, pwd: password, c_id: rawCourseId, card: cardNumber } = body || {};
    if (!name || !email || !rawCourseId || !cardNumber) throw new ValidationError();

    const validPassword = password === undefined || password === null || typeof password === 'string';
    if (
        !isFilledString(name)
        || !isFilledString(email) || !EMAIL_PATTERN.test(email)
        || typeof cardNumber !== 'string' || !CARD_NUMBER_PATTERN.test(cardNumber)
        || !validPassword
    ) {
        throw new ValidationError();
    }

    return { name, email, password: password || null, courseId: parsePositiveInteger(rawCourseId), cardNumber };
}

module.exports = { validateCheckoutInput };
