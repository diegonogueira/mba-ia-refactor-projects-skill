const sqlite3 = require('sqlite3');

function openDatabase(filename) {
    const connection = new sqlite3.Database(filename);
    // All transactions share one connection, so they run one at a time.
    let transactionQueue = Promise.resolve();

    const db = {
        run(sql, params = []) {
            return new Promise((resolve, reject) => {
                connection.run(sql, params, function onRun(err) {
                    return err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes });
                });
            });
        },

        get(sql, params = []) {
            return new Promise((resolve, reject) => {
                connection.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
            });
        },

        all(sql, params = []) {
            return new Promise((resolve, reject) => {
                connection.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
            });
        },

        exec(sql) {
            return new Promise((resolve, reject) => {
                connection.exec(sql, (err) => (err ? reject(err) : resolve()));
            });
        },

        close() {
            return new Promise((resolve, reject) => {
                connection.close((err) => (err ? reject(err) : resolve()));
            });
        },

        transaction(work) {
            const result = transactionQueue.then(async () => {
                await db.run('BEGIN IMMEDIATE');
                try {
                    const value = await work();
                    await db.run('COMMIT');
                    return value;
                } catch (err) {
                    await db.run('ROLLBACK').catch((rollbackError) => {
                        err.rollbackError = rollbackError;
                    });
                    throw err;
                }
            });
            transactionQueue = result.catch(() => undefined);
            return result;
        },
    };

    return db;
}

module.exports = { openDatabase };
