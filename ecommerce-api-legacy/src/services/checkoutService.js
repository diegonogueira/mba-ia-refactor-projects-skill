const { createModels } = require('../models');
const { PAYMENT_STATUS } = require('../utils/constants');
const { hashPassword, verifyPassword } = require('../utils/password');
const { NotFoundError, PaymentDeniedError, UnauthorizedError, ValidationError } = require('../utils/errors');

const ALREADY_ENROLLED_MESSAGE = 'Usuário já matriculado neste curso';

function createCheckoutService({ db, paymentGateway, logger }) {
    const { courses, users, enrollments, auditLogs } = createModels(db);

    // A checkout for an existing e-mail acts on that account, so it must carry the account's password.
    // Accounts stored without a credential never authenticate.
    async function authenticate(account, password) {
        if (!password || !(await verifyPassword(password, account.passwordHash))) throw new UnauthorizedError();
    }

    async function assertNotEnrolled(enrollmentModel, userId, courseId) {
        if (await enrollmentModel.findByUserAndCourse({ userId, courseId })) {
            throw new ValidationError(ALREADY_ENROLLED_MESSAGE);
        }
    }

    // Reverses the authorization when the enrollment could not be persisted, so gateway and database never
    // disagree. A failure to reverse is logged and never replaces the original error.
    async function reverseAuthorization({ authorizationId, amount, courseId }) {
        try {
            await paymentGateway.voidAuthorization({ authorizationId, amount });
            await auditLogs.record(`Estorno pagamento ${authorizationId} curso ${courseId}`);
        } catch (reversalError) {
            logger.error(`Falha ao estornar a autorização ${authorizationId}`, reversalError);
        }
    }

    return {
        // Returns the id of the new enrollment. User, enrollment, payment and audit log are written atomically.
        async checkout({ name, email, password, courseId, cardNumber }) {
            const course = courseId === null ? null : await courses.findActiveById(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            // Authenticate and refuse the duplicate before charging the card; both are repeated inside the transaction.
            const existingUser = await users.findCredentialsByEmail(email);
            if (existingUser) {
                await authenticate(existingUser, password);
                await assertNotEnrolled(enrollments, existingUser.id, course.id);
            }

            // The KDF costs ~200 ms; deriving it here keeps it out of the transaction that holds the connection.
            const passwordHash = !existingUser && password ? await hashPassword(password) : null;

            const { status, authorizationId } = await paymentGateway.authorize({
                cardNumber,
                amount: course.price,
            });
            if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

            try {
                return await db.transaction(async (tx) => {
                    const models = createModels(tx);

                    const user = await models.users.findCredentialsByEmail(email);
                    // Only when a concurrent request created the account after the first check.
                    if (user && user.id !== existingUser?.id) await authenticate(user, password);
                    if (user) await assertNotEnrolled(models.enrollments, user.id, course.id);

                    const userId = user ? user.id : await models.users.create({ name, email, passwordHash });
                    const enrollmentId = await models.enrollments.create({ userId, courseId: course.id });
                    await models.payments.create({ enrollmentId, amount: course.price, status });
                    await models.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);

                    return enrollmentId;
                });
            } catch (err) {
                await reverseAuthorization({ authorizationId, amount: course.price, courseId: course.id });
                throw err;
            }
        },
    };
}

module.exports = { createCheckoutService };
