const { PAYMENT_STATUS } = require('../utils/constants');

// Simulated gateway: only cards starting with this digit are approved.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

const maskCardNumber = (cardNumber) => `****${cardNumber.replace(/\D/g, '').slice(-VISIBLE_CARD_DIGITS)}`;

function createPaymentGateway({ logger }) {
    return {
        async authorize({ cardNumber, amount }) {
            logger.info(`Processando pagamento de ${amount} no cartão ${maskCardNumber(cardNumber)}`);
            return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
        },
    };
}

module.exports = { createPaymentGateway };
