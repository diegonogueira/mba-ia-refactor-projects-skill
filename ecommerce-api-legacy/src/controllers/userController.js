const { presentUserDeleted } = require('../views/presenters');

function createUserController({ userService }) {
    return {
        async deleteUser(req, res) {
            await userService.deleteUser(req.params.id);
            res.send(presentUserDeleted());
        },
    };
}

module.exports = { createUserController };
