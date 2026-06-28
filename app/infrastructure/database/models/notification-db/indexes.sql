CREATE INDEX idx_notificacao_destinatario  ON Notificacao(destinatario_id);
CREATE INDEX idx_notificacao_tipo          ON Notificacao(tipo);
CREATE INDEX idx_notificacao_lida          ON Notificacao(lida);
CREATE INDEX idx_notificacao_criado_em     ON Notificacao(criado_em);
