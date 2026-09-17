const { serializeFinancialReport } = require('../views/serializers');

function makeReportController({ reportService }) {
    return {
        async financialReport(req, res) {
            const report = await reportService.buildFinancialReport();
            res.json(serializeFinancialReport(report));
        },
    };
}

module.exports = { makeReportController };
