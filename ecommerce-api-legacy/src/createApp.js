const express = require('express');

const { makeAuditLogModel } = require('./models/auditLogModel');
const { makeCourseModel } = require('./models/courseModel');
const { makeEnrollmentModel } = require('./models/enrollmentModel');
const { makeFinancialReportModel } = require('./models/financialReportModel');
const { makePaymentModel } = require('./models/paymentModel');
const { makeUserModel } = require('./models/userModel');
const { makeCheckoutService } = require('./services/checkoutService');
const { makePaymentGateway } = require('./services/paymentGateway');
const { makeReportService } = require('./services/reportService');
const { makeUserService } = require('./services/userService');
const { makeCheckoutController } = require('./controllers/checkoutController');
const { makeReportController } = require('./controllers/reportController');
const { makeUserController } = require('./controllers/userController');
const { buildRoutes } = require('./views/routes');
const { makeAdminGuard } = require('./middlewares/adminGuard');
const { makeErrorHandler } = require('./middlewares/errorHandler');

// Composition root: the only module that knows every layer.
function createApp({ db, settings, logger }) {
    const courseModel = makeCourseModel(db);
    const userModel = makeUserModel(db);
    const enrollmentModel = makeEnrollmentModel(db);
    const paymentModel = makePaymentModel(db);
    const auditLogModel = makeAuditLogModel(db);
    const financialReportModel = makeFinancialReportModel(db);

    const paymentGateway = makePaymentGateway({ apiKey: settings.paymentGatewayKey, logger });
    const checkoutService = makeCheckoutService({
        db, courseModel, userModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, logger,
    });
    const reportService = makeReportService({ financialReportModel });
    const userService = makeUserService({ db, userModel, enrollmentModel, paymentModel });

    if (!settings.adminToken) logger.warn('ADMIN_TOKEN não definido; rotas administrativas estão sem autenticação');

    const app = express();
    app.use(express.json());
    app.use(buildRoutes({
        checkoutController: makeCheckoutController({ checkoutService }),
        reportController: makeReportController({ reportService }),
        userController: makeUserController({ userService }),
        adminGuard: makeAdminGuard({ adminToken: settings.adminToken }),
    }));
    app.use(makeErrorHandler({ logger }));

    return app;
}

module.exports = { createApp };
