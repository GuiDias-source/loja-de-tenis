from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, uuid

# ────────────────────────────────────────────────────────────────────
db = SQLAlchemy()

class Usuario(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    nome       = db.Column(db.String(120),  nullable=False)
    email      = db.Column(db.String(120),  unique=True, nullable=False)
    senha_hash = db.Column(db.String(128),  nullable=False)

    # Helpers --------------------------------------------------------
    def set_password(self, senha_plana):
        self.senha_hash = generate_password_hash(senha_plana)

    def check_password(self, senha_plana):
        return check_password_hash(self.senha_hash, senha_plana)

class Tenis(db.Model):
    id     = db.Column(db.Integer, primary_key=True)
    nome   = db.Column(db.String(120), nullable=False)
    preco  = db.Column(db.Float,      nullable=False)
    imagem = db.Column(db.String(200), nullable=True)

# ────────────────────────────────────────────────────────────────────

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "troque_isto_por_uma_chave_secreta")

    # ► Conexão SQLite; troque a URI para PostgreSQL/MySQL se quiser ◄
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///loja.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "img")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Cria tabelas na 1ª execução -----------------------------------
    with app.app_context():
        db.create_all()

    # ─────────────────────────── Rotas ─────────────────────────────

    # Página inicial
    @app.route("/")
    def home():
        # Lista de “produtos destaque” simulada
        produtos = Tenis.query.all()            
        return render_template("home.html", produtos=produtos)

        # CADASTRO ------------------------------------------------------
    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        if request.method == "POST":
            nome  = request.form.get("nome", "").strip()
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")

            if not all([nome, email, senha]):
                flash("Preencha todos os campos.", "erro")
            elif "@" not in email:
                flash("E‑mail inválido.", "erro")
            elif Usuario.query.filter_by(email=email).first():
                flash("E‑mail já registrado.", "erro")
            else:
                novo = Usuario(nome=nome, email=email)
                novo.set_password(senha)
                db.session.add(novo)
                db.session.commit()
                flash("Usuário cadastrado com sucesso!", "sucesso")
                return redirect(url_for("login"))
        return render_template("cadastro.html")

    # LOGIN ---------------------------------------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")
            user  = Usuario.query.filter_by(email=email).first()

            if not user or not user.check_password(senha):
                flash("Credenciais incorretas.", "erro")
            else:
                session["user_id"] = user.id
                flash(f"Bem‑vindo(a), {user.nome}!", "sucesso")
                return redirect(url_for("perfil"))
        return render_template("login.html")

    # PERFIL (visualizar/editar/excluir) ----------------------------
    @app.route("/perfil", methods=["GET", "POST"])
    def perfil():
        user = None
        if "user_id" in session:
            user = Usuario.query.get(session["user_id"])
        if not user:
            flash("Faça login primeiro.", "erro")
            return redirect(url_for("login"))

        # EDITAR -----------------------------------------------------
        if request.method == "POST" and request.form.get("_acao") == "editar":
            novo_nome  = request.form.get("nome", "").strip()
            novo_email = request.form.get("email", "").strip().lower()
            nova_senha = request.form.get("senha", "")

            if not all([novo_nome, novo_email, nova_senha]):
                flash("Nenhum campo pode ficar vazio.", "erro")
            elif novo_email != user.email and \
                 Usuario.query.filter_by(email=novo_email).first():
                flash("E‑mail já em uso por outro cadastro.", "erro")
            else:
                user.nome = novo_nome
                user.email = novo_email
                user.set_password(nova_senha)
                db.session.commit()
                flash("Dados atualizados!", "sucesso")
                return redirect(url_for("perfil"))

        # EXCLUIR ----------------------------------------------------
        if request.method == "POST" and request.form.get("_acao") == "excluir":
            db.session.delete(user)
            db.session.commit()
            session.pop("user_id", None)
            flash("Conta excluída.", "sucesso")
            return redirect(url_for("home"))

        return render_template("perfil.html", user=user)

    # LOGOUT --------------------------------------------------------
    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash("Até logo!", "sucesso")
        return redirect(url_for("home"))

# -------------- NOVO BLOCO: CRUD de produtos --------------
    # LISTAR + FORM DE NOVO
    @app.route("/produtos", methods=["GET", "POST"])
    def produtos():
        # só permitir acesso se estiver logado – simples
        if "user_id" not in session:
            flash("Faça login para gerenciar produtos.", "erro")
            return redirect(url_for("login"))

        # ADICIONAR NOVO
        if request.method == "POST" and request.form.get("_acao") == "novo":
            nome  = request.form.get("nome", "").strip()
            preco = request.form.get("preco", "").replace(",", ".").strip()
            foto  = request.files.get("imagem")

            if not nome or not preco:
                flash("Nome e preço são obrigatórios.", "erro")
            else:
                try:
                    preco = float(preco)
                except ValueError:
                    flash("Preço inválido.", "erro")
                    return redirect(url_for("produtos"))

                nome_arquivo = None
                if foto and foto.filename:
                    ext = os.path.splitext(foto.filename)[1]
                    nome_arquivo = f"{uuid.uuid4().hex}{ext}"
                    caminho = os.path.join(app.config["UPLOAD_FOLDER"],
                                           secure_filename(nome_arquivo))
                    foto.save(caminho)

                novo = Tenis(nome=nome, preco=preco, imagem=nome_arquivo)
                db.session.add(novo)
                db.session.commit()
                flash("Produto adicionado!", "sucesso")
                return redirect(url_for("produtos"))

        lista = Tenis.query.order_by(Tenis.id.desc()).all()
        return render_template("produtos.html", produtos=lista)

    # EDITAR
    @app.route("/produtos/<int:prod_id>/editar", methods=["POST"])
    def editar_produto(prod_id):
        if "user_id" not in session:
            return redirect(url_for("login"))
        prod = Tenis.query.get_or_404(prod_id)

        nome  = request.form.get("nome", "").strip()
        preco = request.form.get("preco", "").replace(",", ".").strip()
        foto  = request.files.get("imagem")

        if not nome or not preco:
            flash("Nome e preço são obrigatórios.", "erro")
            return redirect(url_for("produtos"))

        try:
            preco = float(preco)
        except ValueError:
            flash("Preço inválido.", "erro")
            return redirect(url_for("produtos"))

        prod.nome = nome
        prod.preco = preco

        if foto and foto.filename:
            # remove antiga se existia
            if prod.imagem:
                antigo = os.path.join(app.config["UPLOAD_FOLDER"], prod.imagem)
                if os.path.exists(antigo):
                    os.remove(antigo)
            # salva nova
            ext = os.path.splitext(foto.filename)[1]
            nome_arquivo = f"{uuid.uuid4().hex}{ext}"
            caminho = os.path.join(app.config["UPLOAD_FOLDER"],
                                   secure_filename(nome_arquivo))
            foto.save(caminho)
            prod.imagem = nome_arquivo

        db.session.commit()
        flash("Produto atualizado!", "sucesso")
        return redirect(url_for("produtos"))

    # EXCLUIR
    @app.route("/produtos/<int:prod_id>/excluir", methods=["POST"])
    def excluir_produto(prod_id):
        if "user_id" not in session:
            return redirect(url_for("login"))
        prod = Tenis.query.get_or_404(prod_id)
        # apaga a imagem associada
        if prod.imagem:
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], prod.imagem)
            if os.path.exists(caminho):
                os.remove(caminho)
        db.session.delete(prod)
        db.session.commit()
        flash("Produto removido.", "sucesso")
        return redirect(url_for("produtos"))

    return app