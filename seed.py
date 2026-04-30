"""
seed.py — Popula o banco com usuários de teste.
Execute UMA VEZ após criar o banco:

    python seed.py
"""

from app import app, db, User

USUARIOS = [
    {
        'name':  'Administrador',
        'email': 'adm@123',
        'senha': 'admin',
        'role':  'admin',
    },
    {
        'name':  'Pedro Suporte',
        'email': 'suporte@gmail.com',
        'senha': '123',
        'role':  'operator',
    },
    {
        'name':  'Cliente Teste',
        'email': 'teste@gmail.com',
        'senha': 'teste',
        'role':  'user',
    },
]

with app.app_context():
    db.create_all()

    for dados in USUARIOS:
        existe = User.query.filter_by(email=dados['email']).first()
        if existe:
            print(f'[SKIP]  {dados["email"]} já existe.')
            continue

        user = User(
            name  = dados['name'],
            email = dados['email'],
            role  = dados['role'],
        )
        user.set_password(dados['senha'])
        db.session.add(user)
        print(f'[OK]    {dados["email"]} criado como {dados["role"]}.')

    db.session.commit()
    print('\nSeed concluído! Usuários disponíveis:')
    for u in User.query.all():
        print(f'  • {u.email} ({u.role}) — nome: {u.name}')
