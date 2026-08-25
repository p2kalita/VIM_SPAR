from flask import Blueprint, Flask, render_template, redirect, request, url_for, flash, session
from flask import Flask, render_template, send_from_directory, jsonify
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import text, or_
from flask import current_app as app
from vim_database.models import *
import markdown
from markupsafe import Markup
from datetime import datetime, timezone

from vim.vim_event_db import get_event_db, Event as EventModel

# ---------------- HOME ROUTE ----------------
@app.route('/')
def home():
    # simply renders homepage template
    return render_template('home.html')

# ---------------- LOGIN ----------------
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email')
        password=request.form.get('password')

        # verify user credentials
        this_user=User.query.filter_by(email=email).first()
        print(this_user.email, len(this_user.password), len(password), this_user.role)
        if this_user:
            if this_user.password==password:
                flash(f"Welcome back, {this_user.name}!", "success")
                # redirect based on role
                if this_user.role=='admin':
                    return redirect('/admin')
                else:
                    return redirect(f'/home/{this_user.id}')
            else:
                flash("Incorrect password. Please try again.", "danger")
                #return"Incorrect Password"
        else:
            flash("User not found. Please register first.", "warning")
            #return "User does not exist first register"
    return render_template('login.html')


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    # handles user registration
    if request.method == 'POST':
        # collecting form data
        name = request.form.get('name')
        email = request.form.get('email')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        password = request.form.get('password')

        # check if user already exists
        this_user = User.query.filter_by(email=email).first()

        if this_user:
            flash("User already registered. Please login instead.", "warning")
            return redirect(url_for('login'))
            # return "User already registered"
        else:
            # create new user and save in db
            new_user = User(name=name, email=email, address=address, pincode=pincode, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please login to continue.", "success")
            return redirect(url_for('login'))

    return render_template('registration.html')

@app.route('/admin',methods=['GET','POST'])
def admin_activities():
    return render_template('vim_admin_dashboard.html')

@app.route('/admin/dashboard',methods=['GET','POST'])
def admin_vim_issues():
    return render_template('vim_admin_events_dashboard.html')


# ─────────────────────────────────────────────────────────────────────────────
# EVENT BROWSER API  (mirrors event_browser/backend/main.py)
# All routes are served by the same Flask dev server — no separate process.
# ─────────────────────────────────────────────────────────────────────────────

VALID_EVENT_ACTIONS = {
    "delete": "deleted", 
    "update": "updated"
    }


@app.route('/api/events', methods=['GET'])
def api_list_events():
    """List events with optional filters and server-side pagination."""
    invoice_id  = request.args.get('invoice_id')
    event_id    = request.args.get('event_id')
    status      = request.args.get('status')
    stage       = request.args.get('stage')
    event_type  = request.args.get('event_type')
    start_time  = request.args.get('start_time')
    end_time    = request.args.get('end_time')
    q           = request.args.get('q')
    page        = max(1, int(request.args.get('page', 1)))
    page_size   = min(500, max(1, int(request.args.get('page_size', 25))))

    db = get_event_db()
    try:
        query = db.query(EventModel)

        if invoice_id:
            query = query.filter(EventModel.invoice_id.ilike(f"%{invoice_id}%"))
        if event_id:
            query = query.filter(EventModel.id.ilike(f"%{event_id}%"))
        if status:
            query = query.filter(EventModel.status == status)
        if stage:
            query = query.filter(EventModel.stage == stage)
        if event_type:
            query = query.filter(EventModel.event_type == event_type)
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(EventModel.created_at >= dt)
            except ValueError:
                pass
        if end_time:
            try:
                dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(EventModel.created_at <= dt)
            except ValueError:
                pass
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(EventModel.invoice_id.ilike(like), EventModel.id.ilike(like))
            )

        total = query.count()
        items = (
            query.order_by(EventModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return jsonify({
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "items":     [e.to_dict() for e in items],
        })
    finally:
        db.close()


@app.route('/api/events/<event_id>', methods=['GET'])
def api_get_event(event_id):
    """Return full detail for a single event."""
    db = get_event_db()
    try:
        event = db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            return jsonify({"error": "Event not found"}), 404
        return jsonify(event.to_dict())
    finally:
        db.close()


@app.route('/api/facets', methods=['GET'])
def api_get_facets():
    """Distinct values for filter dropdowns."""
    db = get_event_db()
    try:
        statuses    = [r[0] for r in db.query(EventModel.status).distinct().all() if r[0]]
        stages      = [r[0] for r in db.query(EventModel.stage).distinct().all() if r[0]]
        event_types = [r[0] for r in db.query(EventModel.event_type).distinct().all() if r[0]]
        return jsonify({"statuses": statuses, "stages": stages, "event_types": event_types})
    finally:
        db.close()


@app.route('/api/events/<event_id>', methods=['DELETE'])
def api_delete_event(event_id):
    """Mark an event as deleted."""
    return _apply_event_action(event_id, "delete")


@app.route('/api/events/<event_id>', methods=['PUT'])
def api_update_event(event_id):
    """Mark an event as updated."""
    return _apply_event_action(event_id, "update")


def _apply_event_action(event_id, action):
    if action not in VALID_EVENT_ACTIONS:
        return jsonify({"error": f"Invalid action '{action}'"}), 400
    db = get_event_db()
    try:
        event = db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            return jsonify({"error": "Event not found"}), 404
        event.status = VALID_EVENT_ACTIONS[action]
        db.commit()
        db.refresh(event)
        return jsonify(event.to_dict())
    finally:
        db.close()


@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({"status": "ok"})
