const { ValidationError } = require('./errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+$/;

const isString = (value) => typeof value === 'string';

// Request field names (usr, eml, pwd, c_id, card) are part of the public contract;
// they are mapped to descriptive names here.
function validateCheckoutInput(body) {
    const { usr: name, eml: email, pwd: password, c_id: courseId, card: cardNumber } = body ?? {};

    if (!name || !email || !courseId || !cardNumber) throw new ValidationError();
    if (!isString(name) || !isString(email) || !isString(cardNumber)) throw new ValidationError();
    if (!EMAIL_PATTERN.test(email)) throw new ValidationError();
    if (password && !isString(password)) throw new ValidationError();

    return { name, email, password: password || null, courseId, cardNumber };
}

module.exports = { validateCheckoutInput };
