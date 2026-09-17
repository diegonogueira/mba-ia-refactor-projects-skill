const { createModels } = require('../models');
const { PAYMENT_STATUS } = require('../utils/constants');
const { NotFoundError, PaymentDeniedError } = require('../utils/errors');

function createCheckoutService({ db, paymentGateway }) {
    const { courses } = createModels(db);

    return {
        // Returns the id of the new enrollment. User, enrollment, payment and audit log are written atomically.
        async checkout({ name, email, password, courseId, cardNumber }) {
            const course = courseId === null ? null : await courses.findActiveById(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            const paymentStatus = await paymentGateway.authorize({ cardNumber, amount: course.price });
            if (paymentStatus !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

            return db.transaction(async (tx) => {
                const { users, enrollments, payments, auditLogs } = createModels(tx);

                const existingUser = await users.findByEmail(email);
                const userId = existingUser ? existingUser.id : await users.create({ name, email, password });
                const enrollmentId = await enrollments.create({ userId, courseId: course.id });
                await payments.create({ enrollmentId, amount: course.price, status: paymentStatus });
                await auditLogs.record(`Checkout curso ${course.id} por ${userId}`);

                return enrollmentId;
            });
        },
    };
}

module.exports = { createCheckoutService };
