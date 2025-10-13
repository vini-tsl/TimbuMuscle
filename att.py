# deletar_usuarios.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Usuario

def menu_principal():
    while True:
        print("\n" + "="*50)
        print("🎯 GERENCIADOR DE USUÁRIOS")
        print("="*50)
        print("1. Listar todos os usuários")
        print("2. Deletar usuário por ID")
        print("3. Deletar usuário por email")
        print("4. Deletar todos os usuários de um tipo")
        print("5. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        with app.app_context():
            if opcao == '1':
                listar_usuarios()
            elif opcao == '2':
                usuario_id = input("Digite o ID do usuário: ").strip()
                if usuario_id.isdigit():
                    deletar_usuario(int(usuario_id))
                else:
                    print("❌ ID inválido")
            elif opcao == '3':
                email = input("Digite o email do usuário: ").strip()
                deletar_por_email(email)
            elif opcao == '4':
                tipo = input("Digite o tipo (usuario/profissional/admin): ").strip()
                deletar_por_tipo(tipo)
            elif opcao == '5':
                print("👋 Saindo...")
                break
            else:
                print("❌ Opção inválida")

def listar_usuarios():
    usuarios = Usuario.query.all()
    print("\n📋 LISTA DE USUÁRIOS:")
    print("-" * 80)
    for usuario in usuarios:
        print(f"ID: {usuario.id:2d} | Nome: {usuario.nome:20s} | Email: {usuario.email:25s} | Tipo: {usuario.tipo:12s}")
    print(f"\nTotal: {len(usuarios)} usuários")

def deletar_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        print(f"❌ Usuário ID {usuario_id} não encontrado")
        return
    
    confirmar = input(f"🗑️  Confirmar deleção de '{usuario.nome}' (email: {usuario.email})? (s/N): ")
    if confirmar.lower() == 's':
        try:
            db.session.delete(usuario)
            db.session.commit()
            print("✅ Usuário deletado com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")

def deletar_por_email(email):
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        print(f"❌ Usuário com email '{email}' não encontrado")
        return
    deletar_usuario(usuario.id)

def deletar_por_tipo(tipo):
    usuarios = Usuario.query.filter_by(tipo=tipo).all()
    if not usuarios:
        print(f"❌ Nenhum usuário do tipo '{tipo}' encontrado")
        return
    
    print(f"\n⚠️  Encontrados {len(usuarios)} usuários do tipo '{tipo}':")
    for u in usuarios:
        print(f"   - {u.nome} (ID: {u.id}, Email: {u.email})")
    
    confirmar = input(f"\n🗑️  Confirmar deleção de TODOS estes {len(usuarios)} usuários? (s/N): ")
    if confirmar.lower() == 's':
        try:
            for usuario in usuarios:
                db.session.delete(usuario)
            db.session.commit()
            print(f"✅ {len(usuarios)} usuários deletados com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    menu_principal()