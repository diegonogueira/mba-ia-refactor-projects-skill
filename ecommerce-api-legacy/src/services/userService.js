function makeUserService({ db, userModel, enrollmentModel, paymentModel }) {
    return {
        // Removes the user together with their enrollments and payments, atomically.
        deleteUser(userId) {
            return db.transaction(async () => {
                await paymentModel.deleteByUserId(userId);
                await enrollmentModel.deleteByUserId(userId);
                return userModel.deleteById(userId);
            });
        },
    };
}

module.exports = { makeUserService };
