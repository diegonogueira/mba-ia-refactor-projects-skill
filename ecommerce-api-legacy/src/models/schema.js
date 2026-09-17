const { hashPassword } = require('../utils/password');
const { PAYMENT_STATUS } = require('../utils/constants');

// AUTOINCREMENT on tables that allow deletes: ids are never reused, so audit log references stay unambiguous.
const SCHEMA = `
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        pass TEXT
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        price REAL NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        course_id INTEGER NOT NULL REFERENCES courses(id)
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER NOT NULL UNIQUE REFERENCES enrollments(id),
        amount REAL NOT NULL,
        status TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY,
        action TEXT NOT NULL,
        created_at DATETIME NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_enrollments_user_id ON enrollments (user_id);
    CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON enrollments (course_id);
`;

async function initSchema(db) {
    await db.exec('PRAGMA foreign_keys = ON');
    await db.exec(SCHEMA);
}

async function seedDatabase(db) {
    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) return;

    const seedUserPassword = await hashPassword('123');
    await db.transaction(async (tx) => {
        const { lastID: userId } = await tx.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', seedUserPassword],
        );
        const { lastID: cleanArchitectureId } = await tx.run(
            'INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
            ['Clean Architecture', 997.00],
        );
        await tx.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', ['Docker', 497.00]);
        const { lastID: enrollmentId } = await tx.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, cleanArchitectureId],
        );
        await tx.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, 997.00, PAYMENT_STATUS.PAID],
        );
    });
}

module.exports = { initSchema, seedDatabase };
