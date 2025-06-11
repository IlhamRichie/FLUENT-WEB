from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app # TAMBAHKAN current_app
from backend.utils.decorators import admin_required
# from backend.auth.services import authenticate_user_service # Ini mungkin tidak ideal untuk admin
from backend.database import get_users_collection
# from backend import bcrypt # HAPUS IMPOR INI
from .services import (
    get_admin_dashboard_data,
    check_and_deactivate_inactive_users_service,
    get_paginated_users_service,
    toggle_user_status_service,
    toggle_admin_privilege_service,
    get_paginated_sessions_service
)
from datetime import datetime, timezone # Pindahkan impor ini ke atas untuk konsistensi

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login_route():
    if 'is_admin' in session and session['is_admin']:
        return redirect(url_for('admin.admin_dashboard_route'))
    
    if request.method == 'POST':
        email = request.form.get('email','').lower()
        password = request.form.get('password')
        users_coll = get_users_collection()
        
        user = users_coll.find_one({"email": email, "is_admin": True})
        
        if user:
            # Akses bcrypt melalui current_app.bcrypt
            if user.get('password') and current_app.bcrypt.check_password_hash(user['password'], password):
                session.clear()
                session['email'] = user['email']
                session['is_admin'] = True
                session['user_id'] = str(user['_id'])
                session.modified = True
                users_coll.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin.admin_dashboard_route'))
            else:
                flash('Invalid admin credentials.', 'danger')
        else:
            flash('Admin account not found or not an admin.', 'danger')
            
    return render_template('admin_login.html')

# ... (sisa route admin lainnya tidak perlu diubah terkait bcrypt) ...
@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard_route():
    check_and_deactivate_inactive_users_service()
    dashboard_data = get_admin_dashboard_data()

    # --- TAMBAHKAN BLOK INI ---
    # Ambil dictionary 'charts' dari data
    charts_data = dashboard_data.pop('charts', {}) 
    
    # Gabungkan data utama dengan data charts
    final_data_for_template = {**dashboard_data, **charts_data}
    # --- AKHIR BLOK TAMBAHAN ---

    # Kirim data yang sudah digabung ke template
    return render_template('admin_dashboard.html', **final_data_for_template)

@admin_bp.route('/users')
@admin_required
def admin_users_list_route():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('search', '')
    
    users_list, total_pages, _ = get_paginated_users_service(page, per_page, search_query)
    
    return render_template('admin_users_list.html',
                           users=users_list,
                           page=page,
                           total_pages=total_pages,
                           search_query=search_query)

@admin_bp.route('/users/toggle-status/<user_id_str>', methods=['POST'])
@admin_required
def admin_toggle_user_status_route(user_id_str):
    current_admin_id = session.get('user_id')
    message, category = toggle_user_status_service(user_id_str, current_admin_id)
    flash(message, category)
    return redirect(request.referrer or url_for('admin.admin_users_list_route'))

@admin_bp.route('/users/toggle-admin/<user_id_str>', methods=['POST'])
@admin_required
def admin_toggle_admin_privilege_route(user_id_str):
    current_admin_id = session.get('user_id')
    message, category = toggle_admin_privilege_service(user_id_str, current_admin_id)
    flash(message, category)
    return redirect(request.referrer or url_for('admin.admin_users_list_route'))

@admin_bp.route('/sessions')
@admin_required
def admin_sessions_route():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search_email = request.args.get('search_email', '')
    
    sessions_list, total_pages, _ = get_paginated_sessions_service(page, per_page, search_email)
    
    return render_template('admin_sessions.html',
                           sessions=sessions_list,
                           page=page,
                           total_pages=total_pages,
                           search_email=search_email)

@admin_bp.route('/logout')
@admin_required
def admin_logout_route():
    session.pop('email', None)
    session.pop('is_admin', None)
    session.pop('user_id', None)
    session.modified = True
    flash('You have been logged out from the admin panel.', 'success')
    return redirect(url_for('admin.admin_login_route'))