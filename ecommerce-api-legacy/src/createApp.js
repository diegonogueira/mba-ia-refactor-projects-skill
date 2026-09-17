const express = require('express');
const { createModels } = require('./models');
const { createPaymentGateway } = require('./services/paymentGateway');
const { createCheckoutService } = require('./services/checkoutService');
const { createUserService } = require('./services/userService');
const { createCheckoutController } = require('./controllers/checkoutController');
const { createReportController } = require('./controllers/reportController');
const { createUserController } = require('./controllers/userController');
const buildRoutes = require('./views/routes');
const { createAdminGuard } = require('./middlewares/adminGuard');
const { notFoundHandler, createErrorHandler } = require('./middlewares/errorHandler');

function createApp({ db, settings, logger }) {
    const models = createModels(db);
    const paymentGateway = createPaymentGateway({ logger });
    const checkoutService = createCheckoutService({ db, paymentGateway });
    const userService = createUserService({ db });

    const app = express();
    app.use(express.json());
    app.use(buildRoutes({
        checkoutController: createCheckoutController({ checkoutService }),
        reportController: createReportController({ financialReport: models.financialReport }),
        userController: createUserController({ userService }),
        adminGuard: createAdminGuard({ adminToken: settings.adminToken }),
    }));
    app.use(notFoundHandler);
    app.use(createErrorHandler({ logger }));

    return app;
}

module.exports = createApp;
