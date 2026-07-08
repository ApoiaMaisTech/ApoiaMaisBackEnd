INSERT IGNORE INTO Usuario (email, senha_hash, nome, cargo_enum, esta_ativo) 
VALUES ('admin@apoiamais.com', '$2b$12$...HASH...', 'Administrador', 'administrador', TRUE);