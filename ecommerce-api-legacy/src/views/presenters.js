const UNKNOWN_STUDENT = 'Unknown';

const presentCheckout = (enrollmentId) => ({ msg: 'Sucesso', enrollment_id: enrollmentId });

const presentFinancialReport = (courses) => courses.map((course) => ({
    course: course.title,
    revenue: course.revenue,
    students: course.students.map((student) => ({
        student: student.name ?? UNKNOWN_STUDENT,
        paid: student.amountPaid,
    })),
}));

const presentUserDeleted = () => 'Usuário deletado, junto com suas matrículas e pagamentos.';

module.exports = { presentCheckout, presentFinancialReport, presentUserDeleted };
