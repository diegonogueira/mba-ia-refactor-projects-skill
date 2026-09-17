const { validateCheckoutInput } = require('../utils/validators');
const { serializeCheckout } = require('../views/serializers');

function makeCheckoutController({ checkoutService }) {
    return {
        async checkout(req, res) {
            const input = validateCheckoutInput(req.body);
            const { enrollmentId } = await checkoutService.checkout(input);
            res.status(200).json(serializeCheckout(enrollmentId));
        },
    };
}

module.exports = { makeCheckoutController };
