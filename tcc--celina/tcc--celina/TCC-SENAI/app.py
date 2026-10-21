from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
app.secret_key = (
    'sua_chave_secreta_super_segura'  # Necessário para usar o session do Flask!
)
bcrypt = Bcrypt(app)


def conectar_bd():
  return mysql.connector.connect(
      host='localhost', user='root', password='1234', database='almoxarifado'
  )


# --- ROTAS DE NAVEGAÇÃO DE PÁGINAS ---


@app.route('/')
def login():
  return render_template('login.html')


@app.route('/fazer_login', methods=['POST'])
def fazer_login():
  try:
    usuario = request.form.get('usuario')
    senha = request.form.get('senha')

    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM usuarios WHERE user = %s', (usuario,))
    user_bd = cursor.fetchone()
    conn.close()

    if user_bd and bcrypt.check_password_hash(user_bd['password'], senha):
      # SALVA OS DADOS NA SESSÃO DO FLASK
      session['usuario'] = user_bd['user']
      session['permissao'] = user_bd[
          'permissao'
      ]  # Salva 'admin' ou 'user' na sessão

      proxima_pagina = (
          '/adm' if user_bd['permissao'] == 'admin' else '/almoxarifado'
      )
      return jsonify({'status': 'sucesso', 'redirect': proxima_pagina})
    else:
      return (
          jsonify(
              {'status': 'erro', 'mensagem': 'Usuário ou senha incorretos!'}
          ),
          401,
      )

  except Exception as e:
    return jsonify({'status': 'erro', 'mensagem': str(e)}), 500


@app.route('/logout')
def logout():
  session.clear()  # Limpa a sessão ao sair
  return redirect(url_for('login'))


@app.route('/adm')
def adm():
  # Proteção: Qualquer usuário logado pode ver o painel, mas o conteúdo muda se for admin ou user
  if 'usuario' not in session:
    return redirect(url_for('login'))
  return render_template('adm.html')


@app.route('/almoxarifado')
def almoxarifado():
  if 'usuario' not in session:
    return redirect(url_for('login'))

  conn = conectar_bd()
  cursor = conn.cursor(dictionary=True)
  cursor.execute('SELECT * FROM produtos')
  produtos = cursor.fetchall()
  conn.close()
  return render_template('almoxarifado.html', produtos=produtos)


@app.route('/add')
def add():
  if 'usuario' not in session:
    return redirect(url_for('login'))
  return render_template('add.html')


@app.route('/retirada')
def retirada():
  if 'usuario' not in session:
    return redirect(url_for('login'))

  conn = conectar_bd()
  cursor = conn.cursor(dictionary=True)
  cursor.execute('SELECT * FROM produtos WHERE quantidade > 0')
  produtos = cursor.fetchall()
  conn.close()
  return render_template('retirada.html', produtos=produtos)


@app.route('/adicio')
def adicio():
  # EXCLUSIVO PARA ADMINS: Se não for admin, barra o acesso imediatamente
  if 'usuario' not in session or session.get('permissao') != 'admin':
    return redirect(url_for('adm'))
  return render_template('adicio.html')


# --- ROTAS DE AÇÕES (CADASTRAR, ADICIONAR, RETIRAR) ---


@app.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
  # Proteção de segurança na API
  if 'usuario' not in session or session.get('permissao') != 'admin':
    return jsonify({'mensagem': 'Acesso negado. Apenas administradores.'}), 403

  try:
    usuario = request.form.get('usuario')
    senha = request.form.get('senha')
    permissao = request.form.get('permissao', 'user')

    senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO usuarios (user, password, permissao) VALUES (%s, %s, %s)',
        (usuario, senha_hash, permissao),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {'status': 'sucesso', 'mensagem': 'Usuário cadastrado com sucesso!'}
    )
  except Exception as e:
    return jsonify({'status': 'erro', 'mensagem': str(e)}), 400


@app.route('/adicionar_item', methods=['POST'])
def adicionar_item():
  if 'usuario' not in session:
    return jsonify({'mensagem': 'Não autorizado.'}), 401

  try:
    nome = request.form.get('nome')
    quantidade = int(request.form.get('quantidade'))
    categoria = request.form.get('categoria')
    imagem_url = request.form.get('imagem_url')

    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute('SELECT id, quantidade FROM produtos WHERE nome = %s', (nome,))
    produto = cursor.fetchone()

    if produto:
      nova_qtd = produto[1] + quantidade
      if imagem_url:
        cursor.execute(
            'UPDATE produtos SET quantidade = %s, imagem_url = %s WHERE id = %s',
            (nova_qtd, imagem_url, produto[0]),
        )
      else:
        cursor.execute(
            'UPDATE produtos SET quantidade = %s WHERE id = %s',
            (nova_qtd, produto[0]),
        )
    else:
      cursor.execute(
          'INSERT INTO produtos (nome, quantidade, categoria, imagem_url)'
          ' VALUES (%s, %s, %s, %s)',
          (nome, quantidade, categoria, imagem_url),
      )

    cursor.execute(
        'INSERT INTO movimentacoes (produto_nome, tipo, quantidade) VALUES'
        " (%s, 'Entrada', %s)",
        (nome, quantidade),
    )

    conn.commit()
    conn.close()

    return jsonify(
        {'status': 'sucesso', 'mensagem': 'Item adicionado ao estoque!'}
    )
  except Exception as e:
    return jsonify({'status': 'erro', 'mensagem': str(e)}), 400


@app.route('/retirar_item', methods=['POST'])
def retirar_item():
  if 'usuario' not in session:
    return jsonify({'mensagem': 'Não autorizado.'}), 401

  try:
    produto_id = request.form.get('produto_id')
    quantidade_retirada = int(request.form.get('quantidade'))

    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM produtos WHERE id = %s', (produto_id,))
    produto = cursor.fetchone()

    if not produto:
      return (
          jsonify(
              {'status': 'erro', 'mensagem': 'Produto não encontrado!'}
          ),
          404,
      )

    if produto['quantidade'] < quantidade_retirada:
      return (
          jsonify({
              'status': 'erro',
              'mensagem': (
                  'Estoque insuficiente! Disponível:'
                  f" {produto['quantidade']}"
              ),
          }),
          400,
      )

    nova_qtd = produto['quantidade'] - quantidade_retirada
    cursor.execute(
        'UPDATE produtos SET quantidade = %s WHERE id = %s',
        (nova_qtd, produto_id),
    )

    cursor.execute(
        'INSERT INTO movimentacoes (produto_nome, tipo, quantidade) VALUES'
        " (%s, 'Saída', %s)",
        (produto['nome'], quantidade_retirada),
    )

    conn.commit()
    conn.close()

    return jsonify(
        {'status': 'sucesso', 'mensagem': 'Retirada realizada com sucesso!'}
    )
  except Exception as e:
    return jsonify({'status': 'erro', 'mensagem': str(e)}), 400




######################################## Api#####E



# --- API DE PRODUTOS ---

# --- NOVAS ROTAS DE API LIVRES PARA TESTE (GET E POST) ---

# --- API DE PRODUTOS ---

@app.route('/api/produtos', methods=['GET'])
def api_get_produtos():
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome, quantidade, categoria, imagem_url FROM produtos")
        produtos = cursor.fetchall()
        conn.close()
        return jsonify(produtos), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/produtos', methods=['POST'])
def api_post_produto():
    try:
        dados = request.get_json(force=True, silent=True) or request.form
        nome = dados.get('nome')
        quantidade = int(dados.get('quantidade', 0))
        categoria = dados.get('categoria')
        imagem_url = dados.get('imagem_url')

        if not nome or quantidade < 0:
            return jsonify({'erro': 'Dados inválidos ou incompletos'}), 400

        conn = conectar_bd()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO produtos (nome, quantidade, categoria, imagem_url) VALUES (%s, %s, %s, %s)",
            (nome, quantidade, categoria, imagem_url)
        )
        cursor.execute(
            "INSERT INTO movimentacoes (produto_nome, tipo, quantidade) VALUES (%s, 'Entrada', %s)",
            (nome, quantidade)
        )
        conn.commit()
        conn.close()

        return jsonify({'status': 'sucesso', 'mensagem': 'Produto cadastrado via API'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# --- API DE MOVIMENTAÇÕES ---

@app.route('/api/movimentacoes', methods=['GET'])
def api_get_movimentacoes():
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        # Buscará apenas as colunas que você já tem com certeza
        cursor.execute("SELECT id, produto_nome, tipo, quantidade FROM movimentacoes")
        movimentacoes = cursor.fetchall()
        conn.close()
        return jsonify(movimentacoes), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/movimentacoes', methods=['POST'])
def api_post_movimentacao():
    try:
        dados = request.get_json(force=True, silent=True) or request.form
        produto_nome = dados.get('produto_nome')
        tipo = dados.get('tipo')
        quantidade = int(dados.get('quantidade', 0))

        if tipo not in ['Entrada', 'Saída'] or quantidade <= 0:
            return jsonify({'erro': 'Tipo ou quantidade inválidos'}), 400

        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, quantidade FROM produtos WHERE nome = %s", (produto_nome,))
        produto = cursor.fetchone()

        if not produto:
            conn.close()
            return jsonify({'erro': 'Produto não cadastrado no sistema'}), 404

        if tipo == 'Saída' and produto['quantidade'] < quantidade:
            conn.close()
            return jsonify({'erro': 'Estoque insuficiente'}), 400

        nova_qtd = produto['quantidade'] + quantidade if tipo == 'Entrada' else produto['quantidade'] - quantidade
        cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (nova_qtd, produto['id']))

        cursor.execute(
            "INSERT INTO movimentacoes (produto_nome, tipo, quantidade) VALUES (%s, %s, %s)",
            (produto_nome, tipo, quantidade)
        )
        
        conn.commit()
        conn.close()

        return jsonify({'status': 'sucesso', 'mensagem': f'Movimentação de {tipo} registrada'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# --- API DE USUÁRIOS ---

@app.route('/api/usuarios', methods=['GET'])
def api_get_usuarios():
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, user, permissao FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()
        return jsonify(usuarios), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/usuarios', methods=['POST'])
def api_post_usuario():
    try:
        dados = request.get_json(force=True, silent=True) or request.form
        usuario = dados.get('usuario')
        senha = dados.get('senha')
        permissao = dados.get('permissao', 'user')

        if not usuario or not senha:
            return jsonify({'erro': 'Usuário e senha são obrigatórios'}), 400

        # Mantém a criptografia hash usando o bcrypt existente do seu app
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (user, password, permissao) VALUES (%s, %s, %s)",
            (usuario, senha_hash, permissao)
        )
        conn.commit()
        conn.close()

        return jsonify({'status': 'sucesso', 'mensagem': 'Usuário criado com sucesso via API'}), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    