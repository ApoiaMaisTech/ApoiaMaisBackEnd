SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS Arquivo (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    dono_id VARCHAR(36) NOT NULL,
    tipo_dono ENUM('paciente', 'usuario', 'item_loja', 'conquista') NOT NULL,
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    tipo_mime VARCHAR(100) NOT NULL,
    categoria ENUM('avatar', 'midia_ia', 'imagem_item', 'icone_conquista', 'outro') NOT NULL,
    tamanho_bytes BIGINT NOT NULL,
    url TEXT NOT NULL,
    criado_em DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3)
);

CREATE INDEX idx_arquivo_dono_tipo  ON Arquivo(dono_id, tipo_dono); 
CREATE INDEX idx_arquivo_categoria  ON Arquivo(categoria);
CREATE INDEX idx_arquivo_tipo_mime  ON Arquivo(tipo_mime);
CREATE INDEX idx_arquivo_criado_em  ON Arquivo(criado_em);

SET FOREIGN_KEY_CHECKS = 1;