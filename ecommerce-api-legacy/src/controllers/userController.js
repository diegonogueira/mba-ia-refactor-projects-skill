const { validateUserId } = require('../utils/validators');
const { NotFoundError } = require('../utils/errors');
const { presentUserDeleted } = require('../views/presenters');

function createUserController({ userService }) {
    return {
        async deleteUser(req, res) {
            const userId = validateUserId(req.params.id);
            const deleted = await userService.deleteUser(userId);
            if (!deleted) throw new NotFoundError('Usuário não encontrado');
            res.send(presentUserDeleted());
        },
    };
}

module.exports = { createUserController };
