const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

function makePaymentModel(db) {
    return {
        async create({ enrollmentId, amount, status }) {
            const { lastID } = await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]);
            return lastID;
        },

        deleteByUserId(userId) {
            return db.run('DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [userId]);
        },
    };
}

module.exports = { PAYMENT_STATUS, makePaymentModel };
