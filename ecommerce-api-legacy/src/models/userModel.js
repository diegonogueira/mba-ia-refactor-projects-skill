function createUserModel(db) {
    return {
        findByEmail(email) {
            return db.get('SELECT id, name, email FROM users WHERE email = ?', [email]);
        },

        // Receives the derived hash, never the raw password: the KDF runs outside the transaction.
        // Accounts created without a password store no credential instead of a predictable default.
        async create({ name, email, passwordHash = null }) {
            const { lastID } = await db.run(
                'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
                [name, email, passwordHash],
            );
            return lastID;
        },

        async deleteById(userId) {
            const { changes } = await db.run('DELETE FROM users WHERE id = ?', [userId]);
            return changes;
        },
    };
}

module.exports = { createUserModel };
