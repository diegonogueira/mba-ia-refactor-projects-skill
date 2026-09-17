const { PAYMENT_STATUS } = require('../utils/constants');

const FINANCIAL_REPORT_QUERY = `
    SELECT c.id AS course_id,
           c.title AS course_title,
           e.id AS enrollment_id,
           u.name AS student_name,
           p.amount AS payment_amount,
           p.status AS payment_status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users u ON u.id = e.user_id
    LEFT JOIN payments p ON p.enrollment_id = e.id
    ORDER BY c.id, e.id
`;

function createFinancialReportModel(db) {
    return {
        // Revenue counts only PAID payments; each student lists the amount of its payment, if any.
        async build() {
            const rows = await db.all(FINANCIAL_REPORT_QUERY);
            const courses = new Map();

            for (const row of rows) {
                if (!courses.has(row.course_id)) {
                    courses.set(row.course_id, { title: row.course_title, revenue: 0, students: [] });
                }
                if (row.enrollment_id === null) continue;

                const course = courses.get(row.course_id);
                if (row.payment_status === PAYMENT_STATUS.PAID) {
                    course.revenue += row.payment_amount;
                }
                course.students.push({ name: row.student_name, amountPaid: row.payment_amount ?? 0 });
            }

            return [...courses.values()];
        },
    };
}

module.exports = { createFinancialReportModel };
