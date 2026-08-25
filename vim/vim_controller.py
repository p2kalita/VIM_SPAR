from flask import render_template, redirect, request, url_for, flash, session
from flask import Flask, render_template, send_from_directory, jsonify
from sqlalchemy import or_
from datetime import datetime

from vim_database.models import User, Vendor
from vim_database.models import SystemConfiguration
from vim_database.database import db
from functools import wraps

from vim.vim_event_db import get_event_db, Event as EventModel



def register_routes(app):

    # ---------------- AUTH HELPERS ----------------
    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get('role') != 'admin':
                flash("Admin access required.", "danger")
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    # ---------------- HOME ROUTE ----------------
    @app.route('/')
    def home():
        return render_template('home.html')

    # ---------------- USER HOME (post-login) ----------------
    @app.route('/home/<int:user_id>')
    @login_required
    def user_home(user_id):
        if session['user_id'] != user_id:
            flash("You don't have access to that page.", "danger")
            return redirect(url_for('user_home', user_id=session['user_id']))
        return render_template('home.html', user_id=user_id)

    # ---------------- LOGIN ----------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            this_user = User.query.filter_by(Email=email).first()

            if this_user:
                if this_user.PasswordHash == password:
                    session['user_id'] = this_user.UserID
                    session['role'] = this_user.Role
                    flash(f"Welcome back, {this_user.Username}!", "success")
                    if this_user.Role == 'admin':
                        return redirect(url_for('admin_activities'))
                    else:
                        return redirect(url_for('user_home', user_id=this_user.UserID))
                else:
                    flash("Incorrect password. Please try again.", "danger")
            else:
                flash("User not found. Please register first.", "warning")

        return render_template('login.html')

    # ---------------- LOGOUT ----------------
    @app.route('/logout')
    def logout():
        session.clear()
        flash("You've been logged out.", "success")
        return redirect(url_for('login'))

    # ---------------- REGISTER ----------------
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            this_user = User.query.filter_by(Email=email).first()

            if this_user:
                flash("User already registered. Please login instead.", "warning")
                return redirect(url_for('login'))
            else:
                flash("Registration requires an admin-created vendor account. Please contact your administrator.", "warning")
                return redirect(url_for('login'))

        return render_template('registration.html')

    # ---------------- ADMIN ----------------
    @app.route('/admin', methods=['GET', 'POST'])
    @admin_required
    def admin_activities():
        return render_template('vim_admin_dashboard.html')

    # @app.route('/admin/issues', methods=['GET', 'POST'])
    # @admin_required
    # def admin_vim_issues():
    #     return render_template('vim_admin_events_dashboard.html')

    @app.route('/admin/users')
    @admin_required
    def admin_user_activities():

        users = User.query.order_by(User.UserID.desc()).all()

        vendors = Vendor.query.order_by(
            Vendor.VendorName
        ).all()

        return render_template(
            'vim_admin_users.html',
            users=users,
            vendors=vendors
        )

    @app.route('/admin/users/add', methods=['POST'])
    @admin_required
    def admin_add_user():

        try:

            user = User(
                Username=request.form['username'],
                Email=request.form['email'],
                PasswordHash=request.form['password'],
                Role=request.form['role'],
                VendorID=int(request.form['vendor_id']),
                IsActive=bool(
                    int(request.form['is_active'])
                )
            )

            db.session.add(user)
            db.session.commit()

            flash(
                "User created successfully.",
                "success"
            )

        except Exception as ex:

            db.session.rollback()

            flash(
                f"Error : {str(ex)}",
                "danger"
            )

        return redirect(
            url_for('admin_user_activities')
        )
        
    @app.route('/admin/users/toggle/<int:user_id>')
    @admin_required
    def admin_toggle_user(user_id):

        user = User.query.get_or_404(user_id)

        user.IsActive = not user.IsActive

        db.session.commit()

        flash(
            "User status updated.",
            "success"
        )

        return redirect(
            url_for('admin_user_activities')
        )
        
    @app.route('/admin/users/delete/<int:user_id>')
    @admin_required
    def admin_delete_user(user_id):

        user = User.query.get_or_404(user_id)

        db.session.delete(user)

        db.session.commit()

        flash(
            "User deleted successfully.",
            "success"
        )

        return redirect(
            url_for('admin_user_activities')
        )
        
    @app.route(
        '/admin/users/edit/<int:user_id>',
        methods=['GET','POST']
    )
    @admin_required
    def admin_edit_user(user_id):

        user = User.query.get_or_404(user_id)

        vendors = Vendor.query.all()

        if request.method == 'POST':

            user.Username = request.form['username']
            user.Email = request.form['email']
            user.Role = request.form['role']
            user.VendorID = request.form['vendor_id']

            db.session.commit()

            flash(
                "User updated successfully.",
                "success"
            )

            return redirect(
                url_for('admin_user_activities')
            )

        return render_template(
            'vim_admin_user_edit.html',
            user=user,
            vendors=vendors
        )
        
    # -----------------VENDOR Management ------------------------
    
    @app.route('/admin/vendors')
    @admin_required
    def admin_vendor_activities():

        vendors = Vendor.query.order_by(
            Vendor.VendorID.desc()
        ).all()

        return render_template(
            'vim_admin_vendors.html',
            vendors=vendors
        )
    
    @app.route(
        '/admin/vendors/add',
        methods=['POST']
    )
    @admin_required
    def admin_add_vendor():

        try:

            vendor = Vendor(
                VendorName=request.form['vendor_name'],
                GSTNumber=request.form['gst_number'],
                Address=request.form['address'],
                Email=request.form['email'],
                PhoneNumber=request.form['phone'],
                Status=int(request.form['status'])
            )

            db.session.add(vendor)

            db.session.commit()

            flash(
                "Vendor added successfully.",
                "success"
            )

        except Exception as ex:

            db.session.rollback()

            flash(
                str(ex),
                "danger"
            )

        return redirect(
            url_for(
                'admin_vendor_activities'
            )
        )
    
    @app.route(
        '/admin/vendors/edit/<int:vendor_id>',
        methods=['GET', 'POST']
    )
    @admin_required
    def admin_edit_vendor(vendor_id):

        vendor = Vendor.query.get_or_404(
            vendor_id
        )

        if request.method == 'POST':

            vendor.VendorName = request.form['vendor_name']
            vendor.GSTNumber = request.form['gst_number']
            vendor.Address = request.form['address']
            vendor.Email = request.form['email']
            vendor.PhoneNumber = request.form['phone']
            vendor.Status = int(
                request.form['status']
            )

            db.session.commit()

            flash(
                "Vendor updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    'admin_vendor_activities'
                )
            )

        return render_template(
            'vim_admin_vendor_edit.html',
            vendor=vendor
        )
        
    @app.route(
        '/admin/vendors/toggle/<int:vendor_id>'
    )
    @admin_required
    def admin_toggle_vendor(vendor_id):

        vendor = Vendor.query.get_or_404(
            vendor_id
        )

        if vendor.Status == 1:
            vendor.Status = 0
        else:
            vendor.Status = 1

        db.session.commit()

        flash(
            "Vendor status updated.",
            "success"
        )

        return redirect(
            url_for(
                'admin_vendor_activities'
            )
        )
    
    @app.route(
        '/admin/vendors/delete/<int:vendor_id>'
    )
    @admin_required
    def admin_delete_vendor(vendor_id):

        vendor = Vendor.query.get_or_404(
            vendor_id
        )

        try:

            db.session.delete(vendor)

            db.session.commit()

            flash(
                "Vendor deleted successfully.",
                "success"
            )

        except Exception as ex:

            db.session.rollback()

            flash(
                f"Cannot delete vendor. {str(ex)}",
                "danger"
            )

        return redirect(
            url_for(
                'admin_vendor_activities'
            )
        )
    
    # -----------------SYSTEM CONFIGURATION ---------------------
    @app.route(
        '/admin/settings',
        methods=['GET','POST']
    )
    @admin_required
    def admin_settings():

        config = SystemConfiguration.query.first()

        if not config:

            config = SystemConfiguration()

            db.session.add(config)

            db.session.commit()

        if request.method == 'POST':

            config.AppName = request.form[
                'app_name'
            ]

            config.Environment = request.form[
                'environment'
            ]

            config.Currency = request.form[
                'currency'
            ]

            config.LLMProvider = request.form[
                'llm_provider'
            ]

            config.ModelName = request.form[
                'model_name'
            ]

            config.Temperature = float(
                request.form['temperature']
            )

            config.OCRProvider = request.form[
                'ocr_provider'
            ]

            config.ConfidenceThreshold = float(
                request.form[
                    'confidence_threshold'
                ]
            )

            config.ApprovalLevels = int(
                request.form[
                    'approval_levels'
                ]
            )

            config.AutoApproveLimit = float(
                request.form[
                    'auto_approve_limit'
                ]
            )

            config.SMTPServer = request.form[
                'smtp_server'
            ]

            config.SMTPPort = int(
                request.form[
                    'smtp_port'
                ]
            )

            config.OpenAIKey = request.form[
                'openai_key'
            ]

            config.GeminiKey = request.form[
                'gemini_key'
            ]

            db.session.commit()

            flash(
                "Configuration updated successfully.",
                "success"
            )

        return render_template(
            "vim_admin_settings.html",
            config=config
        )
    
    # ---------------- INTELLIGENT INVOICE UPLOAD ----------------
    @app.route('/admin/invoice_upload', methods=['GET', 'POST'])
    @admin_required
    def admin_invoice_upload():
        from flask import current_app
        from vim.extraction import config as extraction_config

        results = []

        # Read directly from ..env file (avoids stale app.config from wrong server instance)
        llama_key, groq_key = extraction_config._read_keys()
        current_app.config["LLAMA_CLOUD_API_KEY"] = llama_key
        current_app.config["GROQ_API_KEY"] = groq_key
        extraction_config.LLAMA_CLOUD_API_KEY = llama_key
        extraction_config.GROQ_API_KEY = groq_key
        keys_ok = bool(llama_key and groq_key)

        if request.method == 'POST' and keys_ok:
            files = request.files.getlist('invoice_files')
            if not files or all(not f.filename for f in files):
                flash("Please select at least one invoice file.", "warning")
                return redirect(url_for('admin_invoice_upload'))

            from vim.extraction.service import process_uploaded_file

            success_count = 0
            for f in files:
                if not f.filename:
                    continue
                try:
                    record = process_uploaded_file(f)
                    results.append(record)
                    if record.get("status") == "success":
                        success_count += 1
                except ValueError as e:
                    flash(str(e), "danger")
                except OSError as e:
                    flash(str(e).strip(), "danger")
                    break
                except Exception as e:
                    flash(f"Failed to process {f.filename}: {e}", "danger")

            if success_count:
                flash(f"Successfully extracted {success_count} invoice(s).", "success")
        elif request.method == 'POST' and not keys_ok:
            flash(
                "API keys not loaded. Save ..env in the project root and restart the server.",
                "danger",
            )

        return render_template('invoice_upload.html', results=results, keys_ok=keys_ok)

    # ---------------- INVOICE DATA EXTRACTION REVIEW ----------------
    @app.route('/admin/invoice_extraction', methods=['GET'])
    @admin_required
    def admin_invoice_extraction():
        from vim.extraction.json_store import load_all, ENRICHED_PATH

        records = load_all()
        rows = []
        for i, rec in enumerate(reversed(records)):
            rows.append({
                "index": len(records) - 1 - i,
                "file_name": rec.get("file_name") or rec.get("stored_file_name") or "—",
                "vendor_name": rec.get("vendor_name") or "—",
                "invoice_number": rec.get("invoice_number") or "—",
                "invoice_date": rec.get("invoice_date") or "—",
                "amount": rec.get("total_due") or "—",
                "currency": rec.get("currency") or "",
                "status": "Failed" if rec.get("_extraction_error") else (
                    "NeedsReview" if rec.get("_validation_issues") else "Success"
                ),
                "line_item_count": len(rec.get("line_items") or []),
            })

        return render_template(
            'invoice_extraction.html',
            extractions=rows,
            json_path=str(ENRICHED_PATH),
        )

    @app.route('/admin/invoice_extraction/<int:record_index>', methods=['GET'])
    @admin_required
    def admin_invoice_extraction_detail(record_index):
        import json
        from vim.extraction.json_store import load_all

        records = load_all()
        if record_index < 0 or record_index >= len(records):
            flash("Extraction record not found.", "warning")
            return redirect(url_for('admin_invoice_extraction'))

        record = records[record_index]
        return render_template(
            'invoice_extraction_detail.html',
            record=record,
            record_index=record_index,
            record_json=json.dumps(record, indent=2, default=str),
        )

    @app.route('/admin/invoice_extraction/download', methods=['GET'])
    @admin_required
    def admin_invoice_extraction_download():
        from flask import send_file
        from vim.extraction.json_store import ENRICHED_PATH, load_all, save_all

        if not ENRICHED_PATH.exists():
            save_all(load_all())
        if not ENRICHED_PATH.exists():
            flash("No extractions yet. Upload an invoice first.", "warning")
            return redirect(url_for('admin_invoice_upload'))

        return send_file(ENRICHED_PATH, as_attachment=True, download_name="enriched.json")





    # ─────────────────────────────────────────────────────────────────────────────
    # EVENT BROWSER API  (mirrors event_browser/backend/main.py)
    # All routes are served by the same Flask dev server — no separate process.
    # ─────────────────────────────────────────────────────────────────────────────

    VALID_EVENT_ACTIONS = {
        "delete": "deleted", 
        "update": "updated"
        }
    
    @app.route('/admin/issues', methods=['GET', 'POST'])
    @admin_required
    def admin_vim_issues():
        return render_template('vim_admin_events_dashboard.html')

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


    # ─────────────────────────────────────────────────────────────────────────────
    # RAG — AI Assistant  (ChromaDB + CrewAI + Gemini)
    # ─────────────────────────────────────────────────────────────────────────────

    @app.route('/admin/ai_assistant', methods=['GET'])
    @admin_required
    def admin_ai_assistant():
        """Landing page: vendor selector + per-vendor RAG stats."""
        from vim.rag.store import get_vendor_data
        vendors = Vendor.query.order_by(Vendor.VendorName).all()

        vendor_id = request.args.get('vendor_id', '').strip().lower().replace(' ', '_')
        data = None
        selected_vendor = None
        if vendor_id:
            try:
                data = get_vendor_data(vendor_id)
            except Exception as e:
                flash(f"RAG store error: {e}", "danger")
            selected_vendor = vendor_id

        return render_template(
            'vim_rag_assistant.html',
            vendors=vendors,
            selected_vendor=selected_vendor,
            data=data,
        )

    @app.route('/admin/rag_ingest', methods=['POST'])
    @admin_required
    def admin_rag_ingest():
        """Ingest PDF/TXT invoice files or pasted text into ChromaDB."""
        import io as _io
        from pathlib import Path as _Path
        from vim.rag.store import ingest_invoice

        vendor_id = request.form.get('vendor_id', '').strip().lower().replace(' ', '_')
        invoice_number = request.form.get('invoice_number', '').strip()
        raw_text = request.form.get('raw_text', '').strip()
        files = request.files.getlist('invoice_files')
        results = []

        if files:
            for f in files:
                if not f.filename:
                    continue
                stem = _Path(f.filename).stem
                inv_num = invoice_number if invoice_number else stem
                content = f.read()

                text = ""
                if f.filename.lower().endswith('.pdf'):
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(_io.BytesIO(content))
                        text = "\n".join(page.extract_text() or "" for page in reader.pages)
                    except Exception as e:
                        results.append(f"❌ <b>{f.filename}</b>: PDF extraction error — {e}")
                        continue
                elif f.filename.lower().endswith('.txt'):
                    text = content.decode('utf-8', errors='replace')
                else:
                    results.append(f"❌ <b>{f.filename}</b>: Unsupported format (use PDF or TXT).")
                    continue

                if not text.strip():
                    results.append(f"❌ <b>{f.filename}</b>: File was empty.")
                    continue

                try:
                    chunks = ingest_invoice(tenant_id=vendor_id, invoice_number=inv_num, text=text)
                    results.append(
                        f"✅ <b>{f.filename}</b> (Invoice: <code>{inv_num}</code>) "
                        f"→ Indexed <b>{chunks}</b> chunk(s) under <code>vendor_id='{vendor_id}'</code>"
                    )
                except Exception as e:
                    results.append(f"❌ <b>{f.filename}</b>: Ingestion error — {e}")

        if raw_text:
            inv_num = invoice_number if invoice_number else "PASTED-INV"
            try:
                chunks = ingest_invoice(tenant_id=vendor_id, invoice_number=inv_num, text=raw_text)
                results.append(
                    f"✅ Pasted Text (Invoice: <code>{inv_num}</code>) "
                    f"→ Indexed <b>{chunks}</b> chunk(s) under <code>vendor_id='{vendor_id}'</code>"
                )
            except Exception as e:
                results.append(f"❌ Pasted Text Error: {e}")

        if not results:
            results.append("⚠️ No files or text were provided.")

        vendors = Vendor.query.order_by(Vendor.VendorName).all()
        return render_template(
            'vim_rag_ingest_results.html',
            vendor_id=vendor_id,
            results=results,
            vendors=vendors,
        )

    @app.route('/admin/rag_query', methods=['POST'])
    @admin_required
    def admin_rag_query():
        """Query the RAG — retrieves from ChromaDB then synthesizes via CrewAI."""
        from vim.rag.store import retrieve_chunks
        from vim.rag.query_crew import QueryCrew

        vendor_id = request.form.get('vendor_id', '').strip().lower().replace(' ', '_')
        query = request.form.get('query', '').strip()
        invoice_filter = request.form.get('invoice_filter', '').strip() or None

        if not vendor_id or not query:
            flash("Vendor and question are required.", "warning")
            return redirect(url_for('admin_ai_assistant'))

        # Retrieve raw chunks
        raw_chunks = []
        try:
            raw_chunks = retrieve_chunks(
                tenant_id=vendor_id,
                query=query,
                invoice_number=invoice_filter,
                top_k=3,
            )
            for c in raw_chunks:
                dist = c.get("distance")
                c["score_str"] = f"{1 - dist:.3f}" if dist is not None else "N/A"
        except Exception as e:
            flash(f"Retrieval error: {e}", "danger")

        # Synthesize with CrewAI
        answer = ""
        try:
            crew = QueryCrew()
            answer = crew.run(
                tenant_id=vendor_id,
                query=query,
                invoice_number=invoice_filter,
            )
        except Exception as e:
            answer = f"Agent execution error: {e}"

        vendors = Vendor.query.order_by(Vendor.VendorName).all()
        return render_template(
            'vim_rag_query_results.html',
            vendor_id=vendor_id,
            query=query,
            filter_display=invoice_filter or "All Invoices",
            answer=answer,
            raw_chunks=raw_chunks,
            vendors=vendors,
        )
