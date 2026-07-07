CREATE INDEX idx_logacao_usuario_data ON LogAcao(usuario_id, criado_em);
CREATE INDEX idx_logacao_entidade     ON LogAcao(entidade);
CREATE INDEX idx_logacao_acao         ON LogAcao(acao);
CREATE INDEX idx_logacao_criado_em    ON LogAcao(criado_em);

CREATE INDEX idx_logerro_servico_nivel ON LogErro(servico, nivel);
CREATE INDEX idx_logerro_usuario       ON LogErro(usuario_id);
CREATE INDEX idx_logerro_criado_em     ON LogErro(criado_em)