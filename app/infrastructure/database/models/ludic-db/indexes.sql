CREATE INDEX idx_paciente_responsavel  ON Paciente(responsavel_id);
CREATE INDEX idx_paciente_nivel        ON Paciente(nivel_atual);
CREATE INDEX idx_paciente_emocao       ON Paciente(emocao_atual);

CREATE INDEX idx_fase_mundo            ON Fase(mundo_id);
CREATE INDEX idx_fase_ordem            ON Fase(ordem);
CREATE INDEX idx_fase_dificuldade      ON Fase(dificuldade);

CREATE INDEX idx_progresso_paciente    ON ProgressoPaciente(paciente_id);
CREATE INDEX idx_progresso_fase        ON ProgressoPaciente(fase_id);
CREATE INDEX idx_progresso_concluida   ON ProgressoPaciente(foi_concluida);

CREATE INDEX idx_conteudo_paciente     ON ConteudoIA(paciente_id);
CREATE INDEX idx_conteudo_fase         ON ConteudoIA(fase_id);
CREATE INDEX idx_conteudo_tipo         ON ConteudoIA(tipo);

CREATE INDEX idx_mundo_ordem           ON Mundo(ordem);
CREATE INDEX idx_mundo_ativo           ON Mundo(esta_ativo);

CREATE INDEX idx_item_tipo             ON ItemLoja(tipo);
