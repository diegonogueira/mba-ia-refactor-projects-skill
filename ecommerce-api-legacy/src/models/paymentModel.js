function createPaymentModel(db) {
    return {
        async create({ enrollmentId, amount, status }) {
            const { lastID } = await db.run(
                'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
                [enrollmentId, amount, status],
            );
            return lastID;
        },

        async deleteByUserId(userId) {
            const { changes } = await db.run(
                'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
                [userId],
            );
            return changes;
        },
    };
}

module.exports = { createPaymentModel };
