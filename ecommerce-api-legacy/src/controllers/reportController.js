const { presentFinancialReport } = require('../views/presenters');

function createReportController({ financialReport }) {
    return {
        async financialReport(req, res) {
            const courses = await financialReport.build();
            res.json(presentFinancialReport(courses));
        },
    };
}

module.exports = { createReportController };
