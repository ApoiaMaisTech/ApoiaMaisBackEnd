INSERT INTO ItemLoja (id, nome, tipo, preco, url_imagem) VALUES
('i-1', 'Capa de Super-herói', 'acessorio', 50,  'url_capa'),
('i-2', 'Avatar Astronauta',   'avatar',    100, 'url_astro')
ON DUPLICATE KEY UPDATE
    nome       = VALUES(nome),
    preco      = VALUES(preco),
    url_imagem = VALUES(url_imagem);

INSERT INTO Conquista (id, nome, descricao, xp_bonus) VALUES
('ach-1', 'Primeiros Passos', 'Concluiu a primeira fase',    50),
('ach-2', 'Explorador',       'Concluiu um mundo inteiro',  200)
ON DUPLICATE KEY UPDATE
    nome      = VALUES(nome),
    descricao = VALUES(descricao),
    xp_bonus  = VALUES(xp_bonus);
