function makeUserModel(db) {
    return {
        findByEmail(email) {
            return db.get('SELECT id FROM users WHERE email = ?', [email]);
        },

        async create({ name, email, passwordHash }) {
            const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
            return lastID;
        },

        async deleteById(id) {
            const { changes } = await db.run('DELETE FROM users WHERE id = ?', [id]);
            return changes;
        },
    };
}

module.exports = { makeUserModel };
