CREATE INDEX idx_notificacao_destinatario_lida ON Notificacao(destinatario_id, lida);

CREATE INDEX idx_notificacao_tipo      ON Notificacao(tipo);
CREATE INDEX idx_notificacao_criado_em ON Notificacao(criado_em);
