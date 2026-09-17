const { createModels } = require('../models');

function createUserService({ db }) {
    return {
        // Payments and enrollments go with the user, so reports never show orphaned rows.
        async deleteUser(userId) {
            return db.transaction(async (tx) => {
                const { payments, enrollments, users } = createModels(tx);
                await payments.deleteByUserId(userId);
                await enrollments.deleteByUserId(userId);
                return users.deleteById(userId);
            });
        },
    };
}

module.exports = { createUserService };
