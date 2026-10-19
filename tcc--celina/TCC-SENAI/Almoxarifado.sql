CREATE DATABASE almoxarifado;
USE almoxarifado;

-- 1. Tabela de Usuários
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    permissao VARCHAR(20) DEFAULT 'user'
);

-- 2. Tabela de Produtos (Estoque)
CREATE TABLE produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    quantidade INT DEFAULT 0,
    imagem_url VARCHAR(500)
);

-- 3. Tabela de Movimentações (Histórico)
CREATE TABLE movimentacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    quantidade INT NOT NULL
);

INSERT INTO usuarios (user, password, permissao) 
VALUES ('admin', '$2b$12$LKkLGUfUVnNJuwBaqCitMempxTaO4ffEndII2QvSOi0c5.T5WdLCW', 'admin');



=########################
comentario 

se não conseguir acessar usar essse comando dentro do mysql

FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '1234';
FLUSH PRIVILEGES;



se der erro de senha atualizar a biblioteca

pip install --upgrade mysql-connector-python
  