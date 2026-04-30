from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, set_access_cookies,
    unset_jwt_cookies, verify_jwt_in_request, get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta

# ============================================================
#  INICIALIZAÇÃO
# ============================================================
db = SQLAlchemy()
app = Flask(__name__)

# ---- Banco de Dados ----------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost:5432/ticketsystem'
(
    'postgresql://'
    'postgres:admin@'
    'localhost:5432/'
    'ticketsystem'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---- JWT ---------------------------------------------------
app.config['JWT_SECRET_KEY']          = 'TROQUE-ESTA-CHAVE-EM-PRODUCAO-abc123xyz'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['JWT_TOKEN_LOCATION']       = ['cookies']
app.config['JWT_COOKIE_SECURE']        = False   # True em produção (HTTPS)
app.config['JWT_COOKIE_CSRF_PROTECT']  = False   # Simplificado para dev local

db.init_app(app)
jwt = JWTManager(app)


# ============================================================
#  MODELO DE USUÁRIO
# ============================================================
class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # Níveis: 'admin' | 'operator' | 'user'
    role          = db.Column(db.String(20), nullable=False, default='user')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}


# ============================================================
#  DECORATOR DE PROTEÇÃO DE ROTA
# ============================================================
def login_required(f):
    """Redireciona para /login se não houver JWT válido no cookie."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ============================================================
#  ROTAS DE AUTENTICAÇÃO
# ============================================================
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('login', '').strip()
        senha = request.form.get('senha', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(senha):
            # Cria o token JWT com informações do usuário
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={
                    'name': user.name,
                    'role': user.role
                }
            )
            response = make_response(redirect(url_for('home')))
            set_access_cookies(response, access_token)
            return response

        # Credenciais inválidas — volta ao login com flag de erro
        return render_template('login.html', erro=True)

    return render_template('login.html', erro=False)


@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('login')))
    unset_jwt_cookies(response)
    return response


# ============================================================
#  ROTAS PROTEGIDAS (páginas)
# ============================================================
@app.route('/inicio')
@login_required
def home():
    return render_template('home.html')


@app.route('/tickets')
@login_required
def tickets():
    return render_template('tickets.html')


# ============================================================
#  API: DADOS DO USUÁRIO LOGADO (consumida pelo JS)
# ============================================================
@app.route('/api/me')
@login_required
def get_me():
    """Retorna os dados do usuário atual para o frontend."""
    claims = get_jwt()
    return jsonify({
        'name': claims.get('name'),
        'role': claims.get('role')
    })


# ============================================================
#  INICIALIZAÇÃO
# ============================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()   # Cria as tabelas se não existirem
    app.run(host='0.0.0.0', port=8080, debug=True)
