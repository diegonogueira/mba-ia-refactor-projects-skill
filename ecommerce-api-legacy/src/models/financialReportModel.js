// One query for the whole report (courses → enrollments → student → first payment),
// ordered so the service can group rows without extra lookups.
const COURSE_ENROLLMENTS_SQL = `
    SELECT c.id     AS course_id,
           c.title  AS course_title,
           e.id     AS enrollment_id,
           u.id     AS user_id,
           u.name   AS student_name,
           p.id     AS payment_id,
           p.amount AS payment_amount,
           p.status AS payment_status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users u ON u.id = e.user_id
    LEFT JOIN payments p ON p.id = (SELECT MIN(id) FROM payments WHERE enrollment_id = e.id)
    ORDER BY c.id, e.id
`;

function makeFinancialReportModel(db) {
    return {
        listCourseEnrollments() {
            return db.all(COURSE_ENROLLMENTS_SQL);
        },
    };
}

module.exports = { makeFinancialReportModel };
