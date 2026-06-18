import datetime
import os
from zoneinfo import ZoneInfo

def get_local_time():
    return datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-key-ticket-system')

# Use SQLite localmente ou PostgreSQL em produção
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ticketsystem.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+pg8000://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload limit

db = SQLAlchemy()
db.init_app(app)

# --- MODELS ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'operator', 'user'
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20), nullable=True)
    sector = db.Column(db.String(100), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_local_time)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario': self.name,
            'email': self.email,
            'telefone': self.phone,
            'setor': self.sector,
            'nivel': self.role,
            'is_admin': self.is_admin,
            'data': self.created_at.strftime('%d/%m/%Y')
        }

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    sector = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)

    def to_dict(self):
        return {
            'id': self.id,
            'cliente': self.name,
            'email': self.email,
            'telefone': self.phone,
            'setor': self.sector,
            'usuario': self.username,
            'data': self.created_at.strftime('%d/%m/%Y')
        }

class Sector(db.Model):
    __tablename__ = 'sectors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manager = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)

    def to_dict(self):
        return {
            'id': self.id,
            'setor': self.name,
            'responsavel': self.manager,
            'data': self.created_at.strftime('%d/%m/%Y')
        }

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    client_name = db.Column(db.String(100), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='aberto') # 'aberto', 'em andamento', 'fechado'
    created_at = db.Column(db.DateTime, default=get_local_time)

    def to_dict(self):
        operator = User.query.get(self.operator_id) if self.operator_id else None
        return {
            'id': self.id,
            'client_id': self.client_id,
            'cliente': self.client_name,
            'operator_id': self.operator_id,
            'operador': operator.name if operator else None,
            'setor_operador': operator.sector if operator else None,
            'titulo': self.title,
            'descricao': self.description,
            'status': self.status,
            'data': self.created_at.strftime('%d/%m/%Y')
        }

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=get_local_time)

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'text': self.text,
            'image_path': self.image_path,
            'created_at': self.created_at.strftime('%H:%M - %d/%m/%Y')
        }


# --- WEB TEMPLATE ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_val = request.form.get('login')
        senha_val = request.form.get('senha')
        
        user = User.query.filter_by(email=login_val, active=True).first()
        if user and check_password_hash(user.password, senha_val):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            return redirect(url_for('login', error='invalid'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/inicio')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    return render_template('home.html', user=user)

@app.route('/tickets')
def tickets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('tickets.html')

@app.route('/cadastros')
def cadastros():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('home'))
    return render_template('cadastros.html', user=user)

@app.route('/relatorios')
def relatorios():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user or user.role == 'user':
        return redirect(url_for('home'))
    return render_template('relatorios.html')



# --- API ENDPOINTS ---
@app.route('/api/me')
def api_me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Usuário inválido'}), 401
    return jsonify({
        'name': user.name,
        'role': user.role,
        'email': user.email
    })

@app.route('/api/stats')
def api_stats():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    user = User.query.get(user_id)
    if user and user.role == 'user':
        abertos = Ticket.query.filter_by(client_id=user.id).filter(Ticket.status != 'fechado').count()
        pendentes = Ticket.query.filter_by(client_id=user.id, status='fechado').count()
    else:
        abertos = Ticket.query.filter_by(status='aberto').count()
        pendentes = Ticket.query.filter_by(status='em andamento').count()
        
    return jsonify({
        'abertos': abertos,
        'pendentes': pendentes
    })

@app.route('/api/reports')
def api_reports():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    user = User.query.get(user_id)
    if not user or user.role == 'user':
        return jsonify({'error': 'Acesso negado'}), 403

    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    operador_id = request.args.get('operador_id')

    base_query = db.session.query(Ticket)
    
    if data_inicio:
        try:
            start_dt = datetime.datetime.strptime(data_inicio, '%Y-%m-%d')
            base_query = base_query.filter(Ticket.created_at >= start_dt)
        except ValueError:
            pass
            
    if data_fim:
        try:
            end_dt = datetime.datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            base_query = base_query.filter(Ticket.created_at <= end_dt)
        except ValueError:
            pass
            
    if operador_id and operador_id.isdigit() and int(operador_id) > 0:
        base_query = base_query.filter(Ticket.operator_id == int(operador_id))

    total = base_query.count()
    aguardando = base_query.filter(Ticket.status == 'aberto').count()
    em_atendimento = base_query.filter(Ticket.status == 'em andamento').count()
    concluido = base_query.filter(Ticket.status == 'fechado').count()

    from sqlalchemy import func
    
    cliente_counts = base_query.with_entities(Ticket.client_name, func.count(Ticket.id)).group_by(Ticket.client_name).all()
    tickets_por_cliente = [{'cliente': c[0], 'count': c[1]} for c in cliente_counts]

    operador_counts = base_query.join(User, Ticket.operator_id == User.id).with_entities(User.name, func.count(Ticket.id)).group_by(User.name).all()
    tickets_por_operador = [{'operador': o[0], 'count': o[1]} for o in operador_counts]

    tickets_por_status = [
        {'status': 'Aberto', 'count': aguardando},
        {'status': 'Em Andamento', 'count': em_atendimento},
        {'status': 'Concluído', 'count': concluido}
    ]

    return jsonify({
        'total': total,
        'aberto': aguardando,
        'em_andamento': em_atendimento,
        'fechado': concluido,
        'tickets_por_cliente': tickets_por_cliente,
        'tickets_por_operador': tickets_por_operador,
        'tickets_por_status': tickets_por_status
    })

@app.route('/api/tickets', methods=['GET', 'POST'])
def api_tickets():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    user = User.query.get(user_id)
    if request.method == 'GET':
        if user.role == 'user':
            tickets = Ticket.query.filter_by(client_id=user.id).all()
        else:
            tickets = Ticket.query.all()
        return jsonify([t.to_dict() for t in tickets])
        
    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('titulo') or not data.get('descricao'):
            return jsonify({'error': 'Dados incompletos'}), 400
            
        new_ticket = Ticket(
            client_id=user.id,
            client_name=user.name,
            title=data['titulo'],
            description=data['descricao'],
            status='aberto'
        )
        db.session.add(new_ticket)
        db.session.commit()
        return jsonify(new_ticket.to_dict()), 201

@app.route('/api/tickets/<int:id>/status', methods=['PUT'])
def api_ticket_status(id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    ticket = Ticket.query.get_or_404(id)
    data = request.json
    if not data or not data.get('status'):
        return jsonify({'error': 'Dados incompletos'}), 400
        
    user = User.query.get(user_id)
    new_status = data['status']
    
    # Validações de regra de negócio
    if new_status == 'em andamento' and ticket.status == 'aberto':
        if user.role == 'user':
            return jsonify({'error': 'Usuários não podem assumir tickets'}), 403
        ticket.operator_id = user.id
    elif new_status == 'em andamento' and ticket.status == 'fechado':
        if user.role == 'user':
            return jsonify({'error': 'Usuários não podem reabrir tickets'}), 403
    elif new_status == 'fechado':
        if ticket.operator_id and ticket.operator_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Apenas o operador vinculado ou um admin pode concluir este ticket'}), 403

    if ticket.status != new_status:
        ticket.status = new_status
        sys_msg = Message(
            ticket_id=ticket.id,
            sender_id=user.id,
            sender_name='Sistema',
            text=f"Status alterado para '{new_status}' por {user.name}."
        )
        db.session.add(sys_msg)
    
    db.session.commit()
    return jsonify(ticket.to_dict())

@app.route('/api/tickets/<int:id>/transfer', methods=['PUT'])
def api_ticket_transfer(id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    ticket = Ticket.query.get_or_404(id)
    data = request.json
    new_operator_id = data.get('operator_id')
    if not new_operator_id:
        return jsonify({'error': 'Dados incompletos'}), 400
        
    user = User.query.get(user_id)
    
    if ticket.operator_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Apenas o operador atual ou um admin pode transferir este ticket'}), 403
        
    new_operator = User.query.get(new_operator_id)
    if not new_operator:
        return jsonify({'error': 'Operador não encontrado'}), 404
        
    ticket.operator_id = new_operator.id
    
    sys_msg = Message(
        ticket_id=ticket.id,
        sender_id=user.id,
        sender_name='Sistema',
        text=f"Ticket transferido para {new_operator.name} por {user.name}."
    )
    db.session.add(sys_msg)
    
    db.session.commit()
    return jsonify(ticket.to_dict())

@app.route('/api/users', methods=['GET', 'POST'])
def api_users():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    if request.method == 'GET':
        users = User.query.filter_by(active=True).all()
        return jsonify([u.to_dict() for u in users])
        
    elif request.method == 'POST':
        data = request.json
        name = data.get('usuario')
        email = data.get('email')
        password = data.get('senha')
        role = data.get('nivel', 'user')
        sector = data.get('setor')
        phone = data.get('telefone')
        is_admin = data.get('is_admin', False)
        
        if not name or not email or not password:
            return jsonify({'error': 'Dados incompletos'}), 400
            
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'E-mail já cadastrado'}), 400
            
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password, role=role, is_admin=is_admin, phone=phone, sector=sector)
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201

@app.route('/api/users/<int:id>', methods=['PUT', 'DELETE'])
def api_manage_user(id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
        
    current_user = User.query.get(user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
        
    target_user = User.query.get_or_404(id)
    
    if request.method == 'DELETE':
        if target_user.id == current_user.id:
            return jsonify({'error': 'Não pode excluir a si mesmo'}), 400
        target_user.active = False
        db.session.commit()
        return jsonify({'success': True})
        
    data = request.json
    target_user.name = data.get('usuario', target_user.name)
    target_user.email = data.get('email', target_user.email)
    target_user.sector = data.get('setor', target_user.sector)
    target_user.role = data.get('nivel', target_user.role)
    target_user.phone = data.get('telefone', target_user.phone)
    if 'is_admin' in data:
        target_user.is_admin = data['is_admin']
    if data.get('senha'):
        target_user.password = generate_password_hash(data['senha'])
    db.session.commit()
    return jsonify(target_user.to_dict())

@app.route('/api/clients/<int:id>', methods=['PUT', 'DELETE'])
def api_manage_client(id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    current_user = User.query.get(user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    target_client = Client.query.get_or_404(id)
    
    if request.method == 'DELETE':
        db.session.delete(target_client)
        db.session.commit()
        return jsonify({'success': True})
        
    data = request.json
    old_email = target_client.email
    user = User.query.filter_by(email=old_email, active=True).first()
    
    target_client.name = data.get('cliente', target_client.name)
    target_client.email = data.get('email', target_client.email)
    target_client.username = data.get('usuario', target_client.username)
    target_client.sector = data.get('setor', target_client.sector)
    target_client.phone = data.get('telefone', target_client.phone)
    
    if user:
        user.name = target_client.name
        user.email = target_client.email
        user.sector = target_client.sector
        user.phone = target_client.phone
        if data.get('senha'):
            user.password = generate_password_hash(data['senha'])
            
    db.session.commit()
    return jsonify(target_client.to_dict())

@app.route('/api/clients', methods=['GET', 'POST'])
def api_clients():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
        
    if request.method == 'GET':
        clients = Client.query.all()
        return jsonify([c.to_dict() for c in clients])
        
    elif request.method == 'POST':
        data = request.json
        name = data.get('cliente')
        email = data.get('email')
        username = data.get('usuario')
        sector = data.get('setor')
        phone = data.get('telefone')
        
        if not name or not email or not username:
            return jsonify({'error': 'Dados incompletos'}), 400
            
        new_client = Client(name=name, email=email, username=username, phone=phone, sector=sector)
        db.session.add(new_client)
        
        if not User.query.filter_by(email=email).first():
            password = data.get('senha', '123')
            hashed_password = generate_password_hash(password)
            new_user = User(name=name, email=email, password=hashed_password, role='user', phone=phone, sector=sector)
            db.session.add(new_user)
            
        db.session.commit()
        return jsonify(new_client.to_dict()), 201

@app.route('/api/sectors/<int:id>', methods=['PUT', 'DELETE'])
def api_manage_sector(id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    current_user = User.query.get(user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    target_sector = Sector.query.get_or_404(id)
    
    if request.method == 'DELETE':
        db.session.delete(target_sector)
        db.session.commit()
        return jsonify({'success': True})
        
    data = request.json
    target_sector.name = data.get('setor', target_sector.name)
    target_sector.manager = data.get('responsavel', target_sector.manager)
    db.session.commit()
    return jsonify(target_sector.to_dict())

@app.route('/api/sectors', methods=['GET', 'POST'])
def api_sectors():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
        
    if request.method == 'GET':
        sectors = Sector.query.all()
        return jsonify([s.to_dict() for s in sectors])
        
    elif request.method == 'POST':
        data = request.json
        name = data.get('setor')
        manager = data.get('responsavel')
        
        if not name or not manager:
            return jsonify({'error': 'Dados incompletos'}), 400
            
        new_sector = Sector(name=name, manager=manager)
        db.session.add(new_sector)
        db.session.commit()
        return jsonify(new_sector.to_dict()), 201

@app.route('/api/check-email', methods=['POST'])
def api_check_email():
    data = request.json
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        session['reset_email'] = email
        return jsonify({'success': True})
    return jsonify({'error': 'E-mail não encontrado'}), 404

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    data = request.json
    new_password = data.get('password')
    email = session.get('reset_email')
    if not email:
        return jsonify({'error': 'Sessão de redefinição expirada'}), 400
    user = User.query.filter_by(email=email, active=True).first()
    if user:
        user.password = generate_password_hash(new_password)
        db.session.commit()
        session.pop('reset_email', None)
        return jsonify({'success': True})
    return jsonify({'error': 'Usuário não encontrado'}), 404

@app.route('/api/tickets/<int:ticket_id>/messages', methods=['GET'])
def get_messages(ticket_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    user = User.query.get(user_id)
    ticket = Ticket.query.get_or_404(ticket_id)
    if user.role == 'user' and ticket.client_name != user.name:
        return jsonify({'error': 'Acesso negado'}), 403
        
    messages = Message.query.filter_by(ticket_id=ticket_id).order_by(Message.created_at.asc()).all()
    return jsonify([m.to_dict() for m in messages])

@app.route('/api/tickets/<int:ticket_id>/messages', methods=['POST'])
def send_message(ticket_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    user = User.query.get(user_id)
    ticket = Ticket.query.get_or_404(ticket_id)
    if user.role == 'user' and ticket.client_name != user.name:
        return jsonify({'error': 'Acesso negado'}), 403
        
    if ticket.status == 'fechado':
        return jsonify({'error': 'Não é possível enviar mensagens. Este ticket já está concluído.'}), 400
        
    if ticket.status == 'aberto' and user.role != 'user':
        return jsonify({'error': 'Não é possível enviar mensagens enquanto o ticket estiver em aberto.'}), 400
        
    text = request.form.get('text', '').strip()
    image_file = request.files.get('image')
    
    if not text and not image_file:
        return jsonify({'error': 'Mensagem vazia'}), 400
        
    image_path = None
    if image_file:
        filename = secure_filename(image_file.filename)
        timestamp = get_local_time().strftime('%Y%m%d%H%M%S%f')
        filename = f"{timestamp}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(save_path)
        image_path = f"/static/uploads/{filename}"
        
    new_message = Message(
        ticket_id=ticket_id,
        sender_id=user.id,
        sender_name=user.name,
        text=text if text else None,
        image_path=image_path
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify(new_message.to_dict()), 201

@app.route('/api/tickets/reset', methods=['DELETE'])
def reset_tickets():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não logado'}), 401
    
    if user_id != 2:
        return jsonify({'error': 'Acesso negado. Apenas o administrador original pode zerar o sistema.'}), 403
        
    try:
        Message.query.delete()
        Ticket.query.delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)