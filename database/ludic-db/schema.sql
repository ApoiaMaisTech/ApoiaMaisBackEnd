SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS Responsavel (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    nome VARCHAR(255) NOT NULL,
    parentesco VARCHAR(50),
    telefone VARCHAR(20),
    email VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Paciente (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    responsavel_id VARCHAR(36),
    nome VARCHAR(255) NOT NULL,
    data_nascimento DATE NOT NULL,
    nivel_atual INT NOT NULL DEFAULT 1,
    experiencia_total INT NOT NULL DEFAULT 0,
    moedas_total INT NOT NULL DEFAULT 0,
    sequencia_dias INT NOT NULL DEFAULT 0,
    interesses JSON,
    emocao_atual VARCHAR(50) DEFAULT 'neutra',
    url_avatar VARCHAR(255),
    notas_clinicas TEXT,
    criado_em DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    atualizado_em DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    FOREIGN KEY (responsavel_id) REFERENCES Responsavel(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ItemLoja (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    nome VARCHAR(255) NOT NULL,
    tipo ENUM('avatar', 'fundo', 'acessorio') NOT NULL,
    preco INT NOT NULL,
    url_imagem VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS InventarioPaciente (
    paciente_id VARCHAR(36) NOT NULL,
    item_id VARCHAR(36) NOT NULL,
    esta_equipado BOOLEAN DEFAULT FALSE,
    data_aquisicao DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (paciente_id, item_id),
    FOREIGN KEY (paciente_id) REFERENCES Paciente(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES ItemLoja(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Conquista (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    icone_url VARCHAR(255),
    xp_bonus INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ConquistaPaciente (
    paciente_id VARCHAR(36) NOT NULL,
    conquista_id VARCHAR(36) NOT NULL,
    data_conquista DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (paciente_id, conquista_id),
    FOREIGN KEY (paciente_id) REFERENCES Paciente(id) ON DELETE CASCADE,
    FOREIGN KEY (conquista_id) REFERENCES Conquista(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Mundo (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    ordem INT NOT NULL,
    esta_ativo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS Fase (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    mundo_id VARCHAR(36) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    ordem INT NOT NULL,
    dificuldade INT NOT NULL DEFAULT 1,
    xp_recompensa INT NOT NULL DEFAULT 50,
    moedas_recompensa INT NOT NULL DEFAULT 10,
    instrucoes TEXT,
    FOREIGN KEY (mundo_id) REFERENCES Mundo(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ProgressoPaciente (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    paciente_id VARCHAR(36) NOT NULL,
    fase_id VARCHAR(36) NOT NULL,
    pontuacao_maxima INT DEFAULT 0,
    estrelas_conquistadas INT DEFAULT 0,
    esta_bloqueada BOOLEAN DEFAULT TRUE,
    foi_concluida BOOLEAN DEFAULT FALSE,
    tentativas INT DEFAULT 0,
    ultima_vez_jogada DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    UNIQUE KEY unq_paciente_fase (paciente_id, fase_id),
    FOREIGN KEY (paciente_id) REFERENCES Paciente(id) ON DELETE CASCADE,
    FOREIGN KEY (fase_id) REFERENCES Fase(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ConteudoIA (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    paciente_id VARCHAR(36) NOT NULL,
    fase_id VARCHAR(36),
    tipo VARCHAR(50) NOT NULL,
    texto_gerado TEXT,
    url_midia VARCHAR(255),
    prompt TEXT,
    criado_em DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    FOREIGN KEY (paciente_id) REFERENCES Paciente(id) ON DELETE CASCADE,
    FOREIGN KEY (fase_id) REFERENCES Fase(id) ON DELETE SET NULL
);

SET FOREIGN_KEY_CHECKS = 1;