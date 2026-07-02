SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS LogAcao (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    usuario_id VARCHAR(36) NOT NULL,   -- referência ao auth-db.Usuario (sem FK)
    entidade VARCHAR(100) NOT NULL,
    entidade_id VARCHAR(36),
    acao ENUM('criar', 'atualizar', 'deletar', 'login', 'logout', 'visualizar') NOT NULL,
    dados_anteriores JSON,
    dados_novos JSON,
    ip VARCHAR(45),
    user_agent TEXT,
    criado_em DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3)
);

CREATE TABLE IF NOT EXISTS LogErro (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    usuario_id VARCHAR(36),            -- referência ao auth-db.Usuario (sem FK, nullable)
    servico VARCHAR(100) NOT NULL,
    mensagem TEXT NOT NULL,
    stack_trace TEXT,
    nivel ENUM('info', 'warning', 'error', 'critical') NOT NULL DEFAULT 'error',
    criado_em DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3)
);

SET FOREIGN_KEY_CHECKS = 1;
