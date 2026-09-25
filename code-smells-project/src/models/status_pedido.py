"""Status dos pedidos. Módulo próprio para o schema e os models usarem sem import circular."""
STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)
ESTADOS_FINAIS = (STATUS_CANCELADO, STATUS_ENTREGUE)
