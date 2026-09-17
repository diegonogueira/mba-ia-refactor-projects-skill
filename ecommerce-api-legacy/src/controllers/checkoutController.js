const { validateCheckoutInput } = require('../utils/validators');
const { presentCheckout } = require('../views/presenters');

function createCheckoutController({ checkoutService }) {
    return {
        async checkout(req, res) {
            const input = validateCheckoutInput(req.body);
            const enrollmentId = await checkoutService.checkout(input);
            res.status(200).json(presentCheckout(enrollmentId));
        },
    };
}

module.exports = { createCheckoutController };
