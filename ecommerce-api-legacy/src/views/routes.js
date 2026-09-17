const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

function buildRoutes({ checkoutController, reportController, userController, adminGuard }) {
    const router = express.Router();

    router.post('/api/checkout', asyncHandler(checkoutController.checkout));
    router.get('/api/admin/financial-report', adminGuard, asyncHandler(reportController.financialReport));
    router.delete('/api/users/:id', adminGuard, asyncHandler(userController.deleteUser));

    return router;
}

module.exports = buildRoutes;
