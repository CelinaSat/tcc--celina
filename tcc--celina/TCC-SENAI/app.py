from flask import Flask, render_template, request, jsonify
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
bcrypt = Bcrypt(app)

def conectar_bd():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="almoxarifado"
    )

# --- ROTAS DE NAVEGAÇÃO DE PÁGINAS ---

# Rota que carrega a tela HTML de Login
@app.route("/")
def login():
    return render_template("login.html")

# Rota que processa o login via POST
@app.route("/fazer_login", methods=["POST"])
def fazer_login():
    try:
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE user = %s", (usuario,))
        user_bd = cursor.fetchone()
        conn.close()

        # Verifica se o usuário existe e se a senha bate com a hash no BD
        if user_bd and bcrypt.check_password_hash(user_bd["password"], senha):
            # Retorna para onde o usuário deve ir dependendo do nível dele
            proxima_pagina = "/adm" if user_bd["permissao"] == "admin" else "/almoxarifado"
            return jsonify({"status": "sucesso", "redirect": proxima_pagina})
        else:
            return jsonify({"status": "erro", "mensagem": "Usuário ou senha incorretos!"}), 401

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/logout")
def logout():
    # Redireciona o usuário de volta para a tela inicial de login
    return render_template("login.html")

@app.route("/adm")
def adm():
    return render_template("adm.html")

@app.route("/almoxarifado")
def almoxarifado():
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos")
    produtos = cursor.fetchall()
    conn.close()
    return render_template("almoxarifado.html", produtos=produtos)

@app.route("/add")
def add():
    return render_template("add.html")

@app.route("/retirada")
def retirada():
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos WHERE quantidade > 0")
    produtos = cursor.fetchall()
    conn.close()
    return render_template("retirada.html", produtos=produtos)

@app.route("/adicio")
def adicio():
    return render_template("adicio.html")


# --- ROTAS DE AÇÕES (CADASTRAR, ADICIONAR, RETIRAR) ---

@app.route("/cadastrar_usuario", methods=["POST"])
def cadastrar_usuario():
    try:
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        permissao = request.form.get("permissao", "user")

        senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (user, password, permissao) VALUES (%s, %s, %s)",
            (usuario, senha_hash, permissao)
        )
        conn.commit()
        conn.close()

        return jsonify({"status": "sucesso", "mensagem": "Usuário cadastrado com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


@app.route("/adicionar_item", methods=["POST"])
def adicionar_item():
    try:
        nome = request.form.get("nome")
        quantidade = int(request.form.get("quantidade"))
        categoria = request.form.get("categoria")
        imagem_url = request.form.get("imagem_url")  # Captura o link da imagem

        conn = conectar_bd()
        cursor = conn.cursor()
        
        # Verifica se o produto já existe no banco
        cursor.execute("SELECT id, quantidade FROM produtos WHERE nome = %s", (nome,))
        produto = cursor.fetchone()

        if produto:
            nova_qtd = produto[1] + quantidade
            # Atualiza quantidade e opcionalmente a URL da imagem se informada
            if imagem_url:
                cursor.execute("UPDATE produtos SET quantidade = %s, imagem_url = %s WHERE id = %s", 
                               (nova_qtd, imagem_url, produto[0]))
            else:
                cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", 
                               (nova_qtd, produto[0]))
        else:
            # Insere novo produto incluindo a imagem_url
            cursor.execute(
                "INSERT INTO produtos (nome, quantidade, categoria, imagem_url) VALUES (%s, %s, %s, %s)", 
                (nome, quantidade, categoria, imagem_url)
            )
        
        # Registrar movimentação de entrada
        cursor.execute(
            "INSERT INTO movimentacoes (produto_nome, tipo, quantidade) VALUES (%s, 'Entrada', %s)", 
            (nome, quantidade)
        )

        conn.commit()
        conn.close()

        return jsonify({"status": "sucesso", "mensagem": "Item adicionado ao estoque!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


@app.route("/retirar_item", methods=["POST"])
def retirar_item():
    try:
        produto_id = request.form.get("produto_id")
        quantidade_retirada = int(request.form.get("quantidade"))

        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
        produto = cursor.fetchone()

        if not produto:
            return jsonify({"status": "erro", "mensagem": "Produto não encontrado!"}), 404

        if produto['quantidade'] < quantidade_retirada:
            return jsonify({"status": "erro", "mensagem": f"Estoque insuficiente! Disponível: {produto['quantidade']}"}), 400

        nova_qtd = produto['quantidade'] - quantidade_retirada
        cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (nova_qtd, produto_id))

        # Registrar movimentação de saída usando o nome exato da coluna no SQL: produto_nome
        cursor.execute("INSERT INTO movimentacoes (produto_nome, tipo, quantidade) VALUES (%s, 'Saída', %s)", 
                       (produto['nome'], quantidade_retirada))

        conn.commit()
        conn.close()

        return jsonify({"status": "sucesso", "mensagem": "Retirada realizada com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400

######################################## Api



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    