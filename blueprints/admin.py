from flask import Blueprint, jsonify
from models import Usuario
from db import db
from sqlalchemy import text

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/debug-users')
def debug_users():
    try:
        usuarios = Usuario.query.all()
        debug_info = []
        
        for usuario in usuarios:
            debug_info.append({
                'id': usuario.id,
                'nome': usuario.nome,
                'email': usuario.email,
                'key': usuario.key,
                'tipo': usuario.tipo,
                'ultimo_acesso': usuario.ultimo_acesso.isoformat() if hasattr(usuario, 'ultimo_acesso') and usuario.ultimo_acesso else 'Nunca'
            })
        
        return jsonify({
            'total_usuarios': len(debug_info),
            'usuarios': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@admin_bp.route('/debug-routes')
def debug_routes():
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)