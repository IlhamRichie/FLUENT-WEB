from flask import current_app
from datetime import datetime, timezone, timedelta
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
from bson.objectid import ObjectId

from backend.database import get_users_collection, get_sessions_collection

def get_admin_dashboard_data():
    users_coll = get_users_collection()
    sessions_coll = get_sessions_collection()

    user_count = users_coll.count_documents({})
    admin_count = users_coll.count_documents({"is_admin": True})
    active_user_count = users_coll.count_documents({"is_active": True})

    today_start_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions = sessions_coll.count_documents({"start_time": {"$gte": today_start_utc}})
    completed_sessions_count = sessions_coll.count_documents({"status": "completed"})
    
    recent_users = list(users_coll.find({}, {"password": 0}) # Jangan kirim password ke template
                                  .sort("created_at", -1) # Urutkan dari yang terbaru
                                  .limit(5)) # Batasi 5 hasil

    charts = {}
    try:
        # User Registration Trend
        reg_data_agg = list(users_coll.aggregate([
            {"$match": {"created_at": {"$ne": None}}},
            {"$project": {"date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "UTC"}}}},
            {"$group": {"_id": "$date", "count": {"$sum": 1}}}, {"$sort": {"_id": 1}}
        ]))
        if reg_data_agg:
            df_reg = pd.DataFrame(reg_data_agg).rename(columns={'_id': 'date'})
            df_reg['date'] = pd.to_datetime(df_reg['date'])
            fig_reg = px.line(df_reg, x='date', y='count', title='User Registration Trend (UTC)')
            charts['registration_chart'] = fig_reg.to_html(full_html=False, include_plotlyjs='cdn')

        # Gender Distribution
        gender_data_agg = list(users_coll.aggregate([{"$group": {"_id": "$gender", "count": {"$sum": 1}}}]))
        if gender_data_agg:
            df_gender = pd.DataFrame(gender_data_agg).rename(columns={'_id': 'gender'})
            df_gender['gender'] = df_gender['gender'].fillna("Not specified") # Handle None/null
            df_gender = df_gender.groupby('gender')['count'].sum().reset_index()
            fig_gender = px.pie(df_gender, names='gender', values='count', title='Gender Distribution')
            charts['gender_chart'] = fig_gender.to_html(full_html=False, include_plotlyjs='cdn')

        # Top 10 Occupations
        occ_data_agg = list(users_coll.aggregate([
            {"$match": {"occupation": {"$ne": None, "$ne": "", "$ne": "Not specified"}}},
            {"$group": {"_id": "$occupation", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}, {"$limit": 10}
        ]))
        if occ_data_agg:
            df_occ = pd.DataFrame(occ_data_agg).rename(columns={'_id': 'occupation'})
            fig_occ = px.bar(df_occ, x='occupation', y='count', title='Top 10 Occupations')
            charts['occupation_chart'] = fig_occ.to_html(full_html=False, include_plotlyjs='cdn')

        # Daily Interview Sessions (Last 30 Days)
        thirty_days_ago_utc = datetime.now(timezone.utc) - timedelta(days=30)
        act_data_agg = list(sessions_coll.aggregate([
            {"$match": {"start_time": {"$gte": thirty_days_ago_utc}}},
            {"$project": {"date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$start_time", "timezone": "UTC"}}}},
            {"$group": {"_id": "$date", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}} # Sort by date ascending for line/bar chart
        ]))
        if act_data_agg:
            df_act = pd.DataFrame(act_data_agg).rename(columns={'_id': 'date'})
            df_act['date'] = pd.to_datetime(df_act['date'])
            fig_act = px.bar(df_act, x='date', y='count', title='Daily Interview Sessions (Last 30 Days, UTC)')
            charts['activity_chart'] = fig_act.to_html(full_html=False, include_plotlyjs='cdn')

    except Exception as e:
        current_app.logger.error(f"Error generating admin dashboard charts: {e}")
        charts = {key: "<p>Error generating chart.</p>" for key in ['registration_chart', 'gender_chart', 'occupation_chart', 'activity_chart']}


    return {
        "user_count": user_count,
        "admin_count": admin_count,
        "active_user_count": active_user_count,
        "today_sessions": today_sessions,
        "completed_sessions_count": completed_sessions_count,
        "charts": charts,
        "all_users": recent_users # <-- TAMBAHKAN KEY INI
    }

def check_and_deactivate_inactive_users_service():
    users_coll = get_users_collection()
    inactivity_days = current_app.config['INACTIVITY_DAYS']
    inactive_threshold = datetime.now(timezone.utc) - timedelta(days=inactivity_days)

    # Filter: last_login is older than threshold, not an admin, and is_active
    query = {
        "last_login": {"$lt": inactive_threshold},
        "is_admin": {"$ne": True},
        "is_active": True
    }
    update_action = {"$set": {"is_active": False}}
    result = users_coll.update_many(query, update_action)

    if result.modified_count > 0:
        current_app.logger.info(f"Deactivated {result.modified_count} inactive users.")
    return result.modified_count

def get_paginated_users_service(page: int, per_page: int, search_query: str = ""):
    users_coll = get_users_collection()
    query_filter = {}
    if search_query:
        regex = {"$regex": search_query, "$options": "i"}
        query_filter["$or"] = [
            {"username": regex}, {"email": regex}, {"occupation": regex}
        ]

    total_users = users_coll.count_documents(query_filter)
    skip_amount = (page - 1) * per_page
    users_cursor = users_coll.find(query_filter, {
        # Proyeksi fields yang dibutuhkan
        "password": 0, "reset_password_token": 0, "reset_token_expiry": 0
    }).sort("created_at", -1).skip(skip_amount).limit(per_page)
    
    users_list = list(users_cursor)
    total_pages = (total_users + per_page - 1) // per_page
    return users_list, total_pages, total_users

def toggle_user_status_service(user_id_str: str, current_admin_id_str: str):
    users_coll = get_users_collection()
    try:
        user_obj_id = ObjectId(user_id_str)
        user_to_toggle = users_coll.find_one({"_id": user_obj_id})

        if not user_to_toggle:
            return "User not found.", "danger"
        
        # Admin tidak bisa menonaktifkan dirinya sendiri
        if str(user_to_toggle['_id']) == current_admin_id_str and user_to_toggle.get('is_admin'):
            return "Admin cannot deactivate their own account.", "warning"
        
        new_status = not user_to_toggle.get('is_active', False)
        users_coll.update_one({"_id": user_obj_id}, {"$set": {"is_active": new_status}})
        action = "Activated" if new_status else "Deactivated"
        return f"User '{user_to_toggle.get('username', 'N/A')}' status changed to {action}.", "success"
    except Exception as e:
        return f"Error toggling user status: {str(e)}", "danger"

def toggle_admin_privilege_service(user_id_str: str, current_admin_id_str: str):
    users_coll = get_users_collection()
    try:
        user_obj_id = ObjectId(user_id_str)
        user_to_toggle = users_coll.find_one({"_id": user_obj_id})

        if not user_to_toggle:
            return "User not found.", "danger"

        if str(user_to_toggle['_id']) == current_admin_id_str:
            return "Admin cannot change their own admin status.", "warning"

        new_admin_status = not user_to_toggle.get('is_admin', False)
        
        # Jika menjadikan admin, pastikan user lokal punya password
        if new_admin_status and user_to_toggle.get('auth_provider') == 'local' and not user_to_toggle.get('password'):
            return f"User '{user_to_toggle.get('username')}' has no local password. Cannot be made admin.", "danger"
        
        users_coll.update_one({"_id": user_obj_id}, {"$set": {"is_admin": new_admin_status}})
        action = "granted admin privileges" if new_admin_status else "revoked admin privileges from"
        return f"User '{user_to_toggle.get('username', 'N/A')}' has been {action}.", "success"
    except Exception as e:
        return f"Error toggling admin status: {str(e)}", "danger"


def get_paginated_sessions_service(page: int, per_page: int, search_user_email: str = ""):
    users_coll = get_users_collection()
    sessions_coll = get_sessions_collection()
    query_filter = {}

    if search_user_email:
        # Cari user_id berdasarkan email
        users_found = list(users_coll.find({"email": {"$regex": search_user_email, "$options":"i"}}, {"_id": 1}))
        user_ids = [u['_id'] for u in users_found]
        if user_ids:
            query_filter["user_id"] = {"$in": user_ids}
        else:
            # Jika tidak ada user dengan email itu, buat query yang tidak akan return apa-apa
            # Atau bisa juga kembalikan list kosong langsung
            return [], 0, 0 # sessions_list, total_pages, total_sessions

    total_sessions = sessions_coll.count_documents(query_filter)
    skip_amount = (page - 1) * per_page
    sessions_cursor = sessions_coll.find(query_filter).sort("start_time", -1).skip(skip_amount).limit(per_page)
    
    processed_sessions = []
    for s_doc in sessions_cursor:
        user_obj = users_coll.find_one({"_id": s_doc.get('user_id')})
        s_doc['username'] = user_obj['username'] if user_obj else "Unknown User"
        s_doc['user_email'] = user_obj['email'] if user_obj else "N/A"
        
        if s_doc.get('status') == 'completed':
            questions_data = s_doc.get("questions", [])
            total_q_score = sum(q.get("evaluation", {}).get("score", 0) for q in questions_data)
            num_q_answered = len([q for q in questions_data if q.get("evaluation")]) # Hitung yg dievaluasi
            s_doc['overall_score'] = round(total_q_score / num_q_answered, 2) if num_q_answered > 0 else 0.0
        else:
            s_doc['overall_score'] = "N/A (Not Completed)"
        processed_sessions.append(s_doc)
        
    total_pages = (total_sessions + per_page - 1) // per_page
    return processed_sessions, total_pages, total_sessions