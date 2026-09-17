const { PAYMENT_STATUS } = require('../models/paymentModel');
const { NotFoundError, PaymentDeniedError } = require('../utils/errors');
const { hashPassword, generateRandomPassword } = require('../utils/password');

function makeCheckoutService({ db, courseModel, userModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, logger }) {
    async function findOrCreateUser({ name, email, password }) {
        const user = await userModel.findByEmail(email);
        if (user) return user.id;

        const passwordHash = await hashPassword(password || generateRandomPassword());
        return userModel.create({ name, email, passwordHash });
    }

    return {
        async checkout({ name, email, password, courseId, cardNumber }) {
            const course = await courseModel.findActiveById(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            const status = await paymentGateway.charge({ cardNumber, amount: course.price });
            if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

            const enrollmentId = await db.transaction(async () => {
                const userId = await findOrCreateUser({ name, email, password });
                const newEnrollmentId = await enrollmentModel.create({ userId, courseId: course.id });
                await paymentModel.create({ enrollmentId: newEnrollmentId, amount: course.price, status });
                await auditLogModel.record(`Checkout curso ${course.id} por ${userId}`);
                return newEnrollmentId;
            });

            logger.info(`Checkout concluído: matrícula ${enrollmentId} no curso ${course.id}`);
            return { enrollmentId };
        },
    };
}

module.exports = { makeCheckoutService };
