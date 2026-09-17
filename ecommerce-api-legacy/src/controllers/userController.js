const USER_DELETED_MESSAGE = 'Usuário deletado, junto com suas matrículas e pagamentos.';

function makeUserController({ userService }) {
    return {
        async remove(req, res) {
            await userService.deleteUser(req.params.id);
            res.send(USER_DELETED_MESSAGE);
        },
    };
}

module.exports = { makeUserController };
