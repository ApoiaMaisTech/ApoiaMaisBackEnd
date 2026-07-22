CREATE INDEX idx_usuario_email    ON Usuario(email);
CREATE INDEX idx_usuario_cargo    ON Usuario(cargo_enum);
CREATE INDEX idx_usuario_ativo    ON Usuario(esta_ativo);
CREATE INDEX idx_usuario_login    ON Usuario(ultimo_login);
