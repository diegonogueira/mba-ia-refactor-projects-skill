function makeCourseModel(db) {
    return {
        findActiveById(id) {
            return db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [id]);
        },
    };
}

module.exports = { makeCourseModel };
