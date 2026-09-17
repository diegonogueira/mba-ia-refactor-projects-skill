const sqlite3 = require('sqlite3');

function promisifyConnection(connection) {
    return {
        run: (sql, params = []) => new Promise((resolve, reject) => {
            connection.run(sql, params, function onRun(err) {
                if (err) return reject(err);
                return resolve({ lastID: this.lastID, changes: this.changes });
            });
        }),
        get: (sql, params = []) => new Promise((resolve, reject) => {
            connection.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        }),
        all: (sql, params = []) => new Promise((resolve, reject) => {
            connection.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        }),
        exec: (sql) => new Promise((resolve, reject) => {
            connection.exec(sql, (err) => (err ? reject(err) : resolve()));
        }),
    };
}

// The app shares a single SQLite connection, so every operation goes through a queue:
// statements from other requests never interleave with an open transaction.
function createDatabase(connection) {
    const direct = promisifyConnection(connection);
    let tail = Promise.resolve();

    function enqueue(task) {
        const result = tail.then(task);
        tail = result.catch(() => {});
        return result;
    }

    return {
        run: (sql, params) => enqueue(() => direct.run(sql, params)),
        get: (sql, params) => enqueue(() => direct.get(sql, params)),
        all: (sql, params) => enqueue(() => direct.all(sql, params)),
        exec: (sql) => enqueue(() => direct.exec(sql)),

        // `work` receives a transaction-scoped executor; using the outer handle inside it would deadlock.
        transaction: (work) => enqueue(async () => {
            await direct.run('BEGIN IMMEDIATE');
            try {
                const result = await work(direct);
                await direct.run('COMMIT');
                return result;
            } catch (err) {
                try {
                    await direct.run('ROLLBACK');
                } catch (rollbackError) {
                    err.rollbackError = rollbackError;
                }
                throw err;
            }
        }),

        close: () => enqueue(() => new Promise((resolve, reject) => {
            connection.close((err) => (err ? reject(err) : resolve()));
        })),
    };
}

function openDatabase(filename) {
    return new Promise((resolve, reject) => {
        const connection = new sqlite3.Database(filename, (err) => {
            if (err) return reject(err);
            return resolve(createDatabase(connection));
        });
    });
}

module.exports = { openDatabase };
