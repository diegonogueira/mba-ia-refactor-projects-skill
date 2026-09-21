const crypto = require('crypto');
const { PAYMENT_STATUS } = require('../utils/constants');

// Simulated gateway: only cards starting with this digit are approved.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

const maskCardNumber = (cardNumber) => `****${cardNumber.replace(/\D/g, '').slice(-VISIBLE_CARD_DIGITS)}`;

function createPaymentGateway({ logger }) {
    return {
        // Returns the authorization reference so the caller can reverse the charge if the enrollment is not persisted.
        async authorize({ cardNumber, amount }) {
            logger.info(`Processando pagamento de ${amount} no cartão ${maskCardNumber(cardNumber)}`);
            const status = cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
            return { status, authorizationId: status === PAYMENT_STATUS.PAID ? crypto.randomUUID() : null };
        },

        async voidAuthorization({ authorizationId, amount }) {
            logger.warn(`Estornando autorização ${authorizationId} de ${amount}`);
        },
    };
}

module.exports = { createPaymentGateway };
