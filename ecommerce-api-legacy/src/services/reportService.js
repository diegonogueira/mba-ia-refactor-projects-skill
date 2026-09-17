const { PAYMENT_STATUS } = require('../models/paymentModel');

const UNKNOWN_STUDENT = 'Unknown';

function makeReportService({ financialReportModel }) {
    return {
        async buildFinancialReport() {
            const rows = await financialReportModel.listCourseEnrollments();
            const courses = new Map();

            for (const row of rows) {
                if (!courses.has(row.course_id)) {
                    courses.set(row.course_id, { title: row.course_title, revenue: 0, students: [] });
                }
                if (row.enrollment_id === null) continue;

                const course = courses.get(row.course_id);
                const hasPayment = row.payment_id !== null;
                if (hasPayment && row.payment_status === PAYMENT_STATUS.PAID) {
                    course.revenue += row.payment_amount;
                }
                course.students.push({
                    name: row.user_id !== null ? row.student_name : UNKNOWN_STUDENT,
                    amountPaid: hasPayment ? row.payment_amount : 0,
                });
            }

            return [...courses.values()];
        },
    };
}

module.exports = { makeReportService };
