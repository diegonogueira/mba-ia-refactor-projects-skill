const { PAYMENT_STATUS } = require('../models/paymentModel');

// Simulated gateway: cards starting with this prefix are approved.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

const maskCardNumber = (cardNumber) => `****${cardNumber.slice(-VISIBLE_CARD_DIGITS)}`;

function makePaymentGateway({ apiKey, logger }) {
    if (!apiKey) logger.warn('PAYMENT_GATEWAY_KEY não definida; usando gateway de pagamento simulado');

    return {
        async charge({ cardNumber, amount }) {
            const status = cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
            logger.info(`Pagamento de ${amount} no cartão ${maskCardNumber(cardNumber)}: ${status}`);
            return status;
        },
    };
}

module.exports = { makePaymentGateway };
