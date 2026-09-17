function serializeCheckout(enrollmentId) {
    return { msg: 'Sucesso', enrollment_id: enrollmentId };
}

function serializeFinancialReport(courses) {
    return courses.map((course) => ({
        course: course.title,
        revenue: course.revenue,
        students: course.students.map((student) => ({ student: student.name, paid: student.amountPaid })),
    }));
}

module.exports = { serializeCheckout, serializeFinancialReport };
