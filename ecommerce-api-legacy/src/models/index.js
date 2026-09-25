const { createUserModel } = require('./userModel');
const { createCourseModel } = require('./courseModel');
const { createEnrollmentModel } = require('./enrollmentModel');
const { createPaymentModel } = require('./paymentModel');
const { createAuditLogModel } = require('./auditLogModel');

// `db` is either the shared database handle or a transaction-scoped executor.
function createModels(db) {
    return {
        users: createUserModel(db),
        courses: createCourseModel(db),
        enrollments: createEnrollmentModel(db),
        payments: createPaymentModel(db),
        auditLogs: createAuditLogModel(db),
    };
}

module.exports = { createModels };
