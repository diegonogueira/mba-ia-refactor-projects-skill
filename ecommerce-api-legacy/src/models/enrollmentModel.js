function createEnrollmentModel(db) {
    return {
        findByUserAndCourse({ userId, courseId }) {
            return db.get(
                'SELECT id FROM enrollments WHERE user_id = ? AND course_id = ?',
                [userId, courseId],
            );
        },

        async create({ userId, courseId }) {
            const { lastID } = await db.run(
                'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
                [userId, courseId],
            );
            return lastID;
        },

        async deleteByUserId(userId) {
            const { changes } = await db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
            return changes;
        },
    };
}

module.exports = { createEnrollmentModel };
