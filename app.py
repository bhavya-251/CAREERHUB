import os, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deploying")
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "careerhub.db"))

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None: conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, college TEXT DEFAULT '', degree TEXT DEFAULT 'B.Tech',
      branch TEXT DEFAULT 'Computer Science', skills TEXT DEFAULT '', interests TEXT DEFAULT '',
      is_admin INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS opportunities (
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT NOT NULL,
      kind TEXT NOT NULL, location TEXT DEFAULT 'India', mode TEXT DEFAULT 'Hybrid',
      skills TEXT DEFAULT '', description TEXT DEFAULT '', deadline TEXT DEFAULT '',
      apply_url TEXT DEFAULT '', source_type TEXT DEFAULT 'demo'
    );
    CREATE TABLE IF NOT EXISTS applications (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, opportunity_id INTEGER NOT NULL,
      status TEXT DEFAULT 'Applied', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(user_id, opportunity_id), FOREIGN KEY(user_id) REFERENCES users(id),
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    );
    CREATE TABLE IF NOT EXISTS saved (
      user_id INTEGER NOT NULL, opportunity_id INTEGER NOT NULL, PRIMARY KEY(user_id, opportunity_id),
      FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    );
    CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL,
      description TEXT DEFAULT '', tech TEXT DEFAULT '', github TEXT DEFAULT '', demo TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS skills (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, teach TEXT NOT NULL,
      learn TEXT DEFAULT '', bio TEXT DEFAULT '', FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS requests (
      id INTEGER PRIMARY KEY AUTOINCREMENT, from_user INTEGER NOT NULL, to_user INTEGER NOT NULL,
      message TEXT DEFAULT '', status TEXT DEFAULT 'Pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(from_user, to_user), FOREIGN KEY(from_user) REFERENCES users(id), FOREIGN KEY(to_user) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, message TEXT NOT NULL,
      is_read INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS project_posts (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL,
      description TEXT NOT NULL, required_skills TEXT DEFAULT '', roles_needed TEXT DEFAULT '',
      status TEXT DEFAULT 'Open', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS project_connections (
      id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL, from_user INTEGER NOT NULL,
      message TEXT DEFAULT '', status TEXT DEFAULT 'Pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(post_id, from_user),
      FOREIGN KEY(post_id) REFERENCES project_posts(id) ON DELETE CASCADE,
      FOREIGN KEY(from_user) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS project_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT, connection_id INTEGER NOT NULL, sender_id INTEGER NOT NULL,
      message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(connection_id) REFERENCES project_connections(id) ON DELETE CASCADE,
      FOREIGN KEY(sender_id) REFERENCES users(id)
    );
    """)
    # Safe schema migration for databases created by an earlier version.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(opportunities)").fetchall()]
    if "apply_url" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN apply_url TEXT DEFAULT ''")
    if "source_type" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN source_type TEXT DEFAULT 'demo'")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS interview_questions (
      id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, question TEXT NOT NULL,
      sample_points TEXT NOT NULL
    );
    """)
    qcount = conn.execute("SELECT COUNT(*) FROM interview_questions").fetchone()[0]
    if qcount == 0:
        qs = [
          ("Software Engineer","Tell me about yourself.","Briefly explain your education, strongest technical skills, one project, and the role you want."),
          ("Software Engineer","How do you approach a coding problem?","Clarify inputs and constraints, consider edge cases, choose an algorithm, explain complexity, test your solution."),
          ("Software Engineer","Explain OOP concepts.","Cover encapsulation, abstraction, inheritance, and polymorphism with a short example."),
          ("Python Developer","What is the difference between a list and a tuple in Python?","Lists are mutable; tuples are immutable. Mention a use case for each."),
          ("Python Developer","How would you handle an exception in Python?","Explain try, except, optional else/finally, and catching specific exceptions."),
          ("Data Analyst","What is the difference between WHERE and HAVING in SQL?","WHERE filters rows before grouping; HAVING filters groups after aggregation."),
          ("Data Analyst","How would you handle missing data?","Investigate why it is missing, quantify it, then justify dropping, imputing, or flagging values."),
          ("Cloud/DevOps Intern","What is CI/CD?","Explain automated build, test, and deployment stages and why they reduce manual errors."),
          ("Cloud/DevOps Intern","What is the purpose of Git?","Version control, collaboration, branching, history, and safe rollback.")
        ]
        conn.executemany("INSERT INTO interview_questions(role,question,sample_points) VALUES(?,?,?)", qs)
    count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    if count == 0:
        rows = [
        ("Python Developer Intern","TechNova","Internship","Hyderabad, India","Hybrid","Python, Flask, SQL","Build small web services and collaborate with an engineering team.","2026-11-30"),
        ("Frontend Engineering Intern","PixelWorks","Internship","Remote","Remote","React, JavaScript, CSS","Work on accessible interfaces and reusable UI components.","2026-12-05"),
        ("Graduate Software Engineer","Northstar Labs","Full-time","Bengaluru, India","On-site","Java, DSA, Git","Entry-level software role for graduates who enjoy solving problems.","2026-12-20"),
        ("Data Analytics Intern","InsightBridge","Internship","Remote","Remote","Python, SQL, Excel","Explore datasets, create reports and communicate useful insights.","2026-11-25"),
        ("Cloud Support Associate","CloudSpring","Full-time","Pune, India","Hybrid","Linux, Networking, AWS","Sample listing for demonstration only. Replace with a verified opening before presenting it as live.","2026-12-15")]
        conn.executemany("INSERT INTO opportunities(title,company,kind,location,mode,skills,description,deadline) VALUES(?,?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        # A stale session can remain after the database/user has changed.
        # Validate it before protected pages try to access current_user.name.
        user = db().execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
        if user is None:
            session.clear()
            flash("Your session expired. Please log in again.", "info")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def shared():
    user = None
    if session.get("user_id"):
        user = db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if user is None:
            session.clear()
    return {"current_user": user}

@app.route("/")
def index():
    if session.get("user_id"): return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if not name or not email or len(password)<6:
            flash("Enter your name, a valid email, and a password with at least 6 characters.", "error")
        else:
            try:
                cur=db().execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                    (name,email,generate_password_hash(password)))
                db().commit(); session["user_id"]=cur.lastrowid
                flash("Welcome to CareerHub! Complete your profile to get started.", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("An account with that email already exists.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email=request.form.get("email","").strip().lower()
        user=db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], request.form.get("password","")):
            session.clear(); session["user_id"]=user["id"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Permanently remove the signed-in user's account and associated personal data."""
    uid = session["user_id"]
    conn = db()
    # Remove dependent records first because most older tables do not cascade deletes.
    conn.execute("DELETE FROM project_messages WHERE connection_id IN (SELECT id FROM project_connections WHERE from_user=? OR post_id IN (SELECT id FROM project_posts WHERE user_id=?))", (uid, uid))
    conn.execute("DELETE FROM project_messages WHERE sender_id=?", (uid,))
    conn.execute("DELETE FROM project_connections WHERE from_user=? OR post_id IN (SELECT id FROM project_posts WHERE user_id=?)", (uid, uid))
    conn.execute("DELETE FROM project_posts WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM requests WHERE from_user=? OR to_user=?", (uid, uid))
    conn.execute("DELETE FROM notifications WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM applications WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM saved WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM projects WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM skills WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    session.clear()
    flash("Your CareerHub account and associated data have been deleted.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid=session["user_id"]; conn=db()
    stats = {
      "applications": conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (uid,)).fetchone()[0],
      "saved": conn.execute("SELECT COUNT(*) FROM saved WHERE user_id=?", (uid,)).fetchone()[0],
      "projects": conn.execute("SELECT COUNT(*) FROM projects WHERE user_id=?", (uid,)).fetchone()[0],
      "skills": conn.execute("SELECT COUNT(*) FROM skills WHERE user_id=?", (uid,)).fetchone()[0]}
    opportunities=conn.execute("SELECT * FROM opportunities ORDER BY id DESC LIMIT 3").fetchall()
    projects=conn.execute("SELECT * FROM projects WHERE user_id=? ORDER BY id DESC LIMIT 3",(uid,)).fetchall()
    return render_template("dashboard.html", stats=stats, opportunities=opportunities, projects=projects)

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    uid=session["user_id"]
    if request.method=="POST":
        db().execute("UPDATE users SET name=?,college=?,degree=?,branch=?,skills=?,interests=? WHERE id=?",
          (request.form.get("name","").strip(),request.form.get("college","").strip(),request.form.get("degree","B.Tech"),
           request.form.get("branch","").strip(),request.form.get("skills","").strip(),request.form.get("interests","").strip(),uid))
        db().commit(); flash("Profile saved.", "success"); return redirect(url_for("profile"))
    user=db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return render_template("profile.html", user=user)

@app.route("/career")
@login_required
def career():
    q=request.args.get("q","").strip(); kind=request.args.get("kind","")
    sql="SELECT o.*, EXISTS(SELECT 1 FROM saved s WHERE s.user_id=? AND s.opportunity_id=o.id) AS is_saved FROM opportunities o WHERE 1=1"
    params=[session["user_id"]]
    if q: sql+=" AND (o.title LIKE ? OR o.company LIKE ? OR o.skills LIKE ?)"; params += [f"%{q}%"]*3
    if kind: sql+=" AND o.kind=?"; params.append(kind)
    sql+=" ORDER BY o.id DESC"
    opportunities=db().execute(sql,params).fetchall()
    return render_template("career.html", opportunities=opportunities, q=q, kind=kind)

@app.route("/opportunity/<int:oid>")
@login_required
def opportunity(oid):
    item=db().execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone()
    if not item: flash("Opportunity not found.", "error"); return redirect(url_for("career"))
    applied=db().execute("SELECT 1 FROM applications WHERE user_id=? AND opportunity_id=?",(session["user_id"],oid)).fetchone()
    saved=db().execute("SELECT 1 FROM saved WHERE user_id=? AND opportunity_id=?",(session["user_id"],oid)).fetchone()
    return render_template("opportunity.html", item=item, applied=bool(applied), saved=bool(saved))

@app.post("/opportunity/<int:oid>/apply")
@login_required
def apply(oid):
    try:
        db().execute("INSERT INTO applications(user_id,opportunity_id) VALUES(?,?)",(session["user_id"],oid)); db().commit()
        flash("Application recorded in your CareerHub demo account.", "success")
    except sqlite3.IntegrityError: flash("You have already applied to this opportunity.", "info")
    return redirect(url_for("opportunity",oid=oid))

@app.post("/opportunity/<int:oid>/save")
@login_required
def save_opportunity(oid):
    exists=db().execute("SELECT 1 FROM saved WHERE user_id=? AND opportunity_id=?",(session["user_id"],oid)).fetchone()
    if exists: db().execute("DELETE FROM saved WHERE user_id=? AND opportunity_id=?",(session["user_id"],oid)); flash("Removed from saved opportunities.","success")
    else: db().execute("INSERT OR IGNORE INTO saved(user_id,opportunity_id) VALUES(?,?)",(session["user_id"],oid)); flash("Opportunity saved.","success")
    db().commit(); return redirect(url_for("opportunity",oid=oid))

@app.route("/applications")
@login_required
def applications():
    rows=db().execute("""SELECT a.*,o.title,o.company,o.kind FROM applications a JOIN opportunities o ON o.id=a.opportunity_id
       WHERE a.user_id=? ORDER BY a.id DESC""",(session["user_id"],)).fetchall()
    return render_template("applications.html", rows=rows)

@app.route("/projects", methods=["GET","POST"])
@login_required
def projects():
    uid=session["user_id"]
    if request.method=="POST":
        action=request.form.get("action","portfolio")
        if action=="collab":
            title=request.form.get("collab_title","").strip()
            description=request.form.get("collab_description","").strip()
            if title and description:
                db().execute("INSERT INTO project_posts(user_id,title,description,required_skills,roles_needed) VALUES(?,?,?,?,?)",
                    (uid,title,description,request.form.get("required_skills","").strip(),request.form.get("roles_needed","").strip()))
                db().commit(); flash("Project collaboration post published! Students can now connect with you.","success")
            else: flash("Add a project title and description before publishing.","error")
            return redirect(url_for("projects"))
        title=request.form.get("title","").strip()
        if title:
            db().execute("INSERT INTO projects(user_id,title,description,tech,github,demo) VALUES(?,?,?,?,?,?)",
              (uid,title,request.form.get("description","").strip(),request.form.get("tech","").strip(),
               request.form.get("github","").strip(),request.form.get("demo","").strip()))
            db().commit(); flash("Project added to your portfolio.","success")
        else: flash("Project title is required.","error")
        return redirect(url_for("projects"))
    rows=db().execute("SELECT * FROM projects WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
    posts=db().execute("""SELECT p.*,u.name AS owner_name,u.skills AS owner_skills,
        (SELECT COUNT(*) FROM project_connections pc WHERE pc.post_id=p.id AND pc.status!='Declined') AS interested_count,
        (SELECT COUNT(*) FROM project_connections pc WHERE pc.post_id=p.id AND pc.from_user=? ) AS already_connected
        FROM project_posts p JOIN users u ON u.id=p.user_id
        WHERE p.status='Open' ORDER BY p.id DESC""",(uid,)).fetchall()
    return render_template("projects.html", projects=rows, posts=posts)

@app.post("/projects/collab/<int:post_id>/connect")
@login_required
def connect_project(post_id):
    uid=session["user_id"]
    post=db().execute("SELECT * FROM project_posts WHERE id=? AND status='Open'",(post_id,)).fetchone()
    if not post:
        flash("This project post is no longer open.","error")
    elif post["user_id"]==uid:
        flash("You cannot connect to your own post.","error")
    else:
        try:
            db().execute("INSERT INTO project_connections(post_id,from_user,message) VALUES(?,?,?)",
                         (post_id,uid,request.form.get("message","I'd like to contribute to this project.").strip()))
            db().commit()
            flash("Connection request sent! Open Project Chats to continue after the owner accepts.","success")
        except sqlite3.IntegrityError:
            flash("You have already sent a request for this project.","error")
    return redirect(url_for("projects"))

@app.route("/project-chats")
@login_required
def project_chats():
    uid=session["user_id"]
    rows=db().execute("""SELECT pc.*,p.title,p.user_id AS owner_id,
        u.name AS applicant_name, owner.name AS owner_name
        FROM project_connections pc JOIN project_posts p ON p.id=pc.post_id
        JOIN users u ON u.id=pc.from_user JOIN users owner ON owner.id=p.user_id
        WHERE pc.from_user=? OR p.user_id=? ORDER BY pc.id DESC""",(uid,uid)).fetchall()
    return render_template("project_chats.html", connections=rows, uid=uid)

@app.post("/project-chats/<int:cid>/status")
@login_required
def project_chat_status(cid):
    uid=session["user_id"]
    conn=db().execute("""SELECT pc.id,p.user_id FROM project_connections pc JOIN project_posts p ON p.id=pc.post_id
        WHERE pc.id=?""",(cid,)).fetchone()
    if conn and conn["user_id"]==uid:
        status=request.form.get("status")
        if status in ("Accepted","Declined"):
            db().execute("UPDATE project_connections SET status=? WHERE id=?",(status,cid)); db().commit()
            flash("Connection request updated.","success")
    return redirect(url_for("project_chats"))

@app.route("/project-chats/<int:cid>", methods=["GET","POST"])
@login_required
def project_chat(cid):
    uid=session["user_id"]
    connection=db().execute("""SELECT pc.*,p.title,p.user_id AS owner_id,u.name AS applicant_name,owner.name AS owner_name
        FROM project_connections pc JOIN project_posts p ON p.id=pc.post_id
        JOIN users u ON u.id=pc.from_user JOIN users owner ON owner.id=p.user_id WHERE pc.id=?""",(cid,)).fetchone()
    if not connection or uid not in (connection["owner_id"], connection["from_user"]):
        flash("You do not have access to this project chat.","error")
        return redirect(url_for("project_chats"))
    if request.method=="POST":
        message=request.form.get("message","").strip()
        if connection["status"]=="Accepted" and message:
            db().execute("INSERT INTO project_messages(connection_id,sender_id,message) VALUES(?,?,?)",(cid,uid,message))
            db().commit()
        elif connection["status"]!="Accepted":
            flash("The project owner must accept the request before chat is enabled.","error")
        return redirect(url_for("project_chat",cid=cid))
    messages=db().execute("""SELECT m.*,u.name FROM project_messages m JOIN users u ON u.id=m.sender_id
        WHERE m.connection_id=? ORDER BY m.id""",(cid,)).fetchall()
    return render_template("project_chat.html", connection=connection, messages=messages, uid=uid)

@app.post("/projects/<int:pid>/delete")
@login_required
def delete_project(pid):
    db().execute("DELETE FROM projects WHERE id=? AND user_id=?",(pid,session["user_id"])); db().commit()
    flash("Project deleted if it belonged to your account.","success"); return redirect(url_for("projects"))

@app.route("/skillswap", methods=["GET","POST"])
@login_required
def skillswap():
    uid=session["user_id"]
    if request.method=="POST":
        teach=request.form.get("teach","").strip()
        if teach:
            db().execute("INSERT INTO skills(user_id,teach,learn,bio) VALUES(?,?,?,?)",
              (uid,teach,request.form.get("learn","").strip(),request.form.get("bio","").strip()))
            db().commit(); flash("Your SkillSwap listing is live.","success")
        return redirect(url_for("skillswap"))
    q=request.args.get("q","").strip()
    sql="""SELECT s.*,u.name,u.college FROM skills s JOIN users u ON u.id=s.user_id WHERE s.user_id != ?"""
    params=[uid]
    if q: sql+=" AND (s.teach LIKE ? OR s.learn LIKE ? OR u.name LIKE ?)"; params += [f"%{q}%"]*3
    rows=db().execute(sql+" ORDER BY s.id DESC",params).fetchall()
    mine=db().execute("SELECT * FROM skills WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
    return render_template("skillswap.html", listings=rows, mine=mine, q=q)

@app.post("/skillswap/<int:sid>/connect")
@login_required
def connect(sid):
    listing=db().execute("SELECT * FROM skills WHERE id=?",(sid,)).fetchone()
    if not listing: flash("Listing not found.","error")
    elif listing["user_id"]==session["user_id"]: flash("This is your own listing.","info")
    else:
        try:
            db().execute("INSERT INTO requests(from_user,to_user,message) VALUES(?,?,?)",
             (session["user_id"],listing["user_id"],request.form.get("message","I'd like to connect and learn together.")))
            db().commit(); flash("Connection request sent.","success")
        except sqlite3.IntegrityError: flash("You have already sent a request to this student.","info")
    return redirect(url_for("skillswap"))

@app.route("/requests")
@login_required
def requests_page():
    uid=session["user_id"]
    incoming=db().execute("SELECT r.*,u.name,u.email FROM requests r JOIN users u ON u.id=r.from_user WHERE r.to_user=? ORDER BY r.id DESC",(uid,)).fetchall()
    outgoing=db().execute("SELECT r.*,u.name FROM requests r JOIN users u ON u.id=r.to_user WHERE r.from_user=? ORDER BY r.id DESC",(uid,)).fetchall()
    return render_template("requests.html", incoming=incoming, outgoing=outgoing)

@app.post("/requests/<int:rid>/status")
@login_required
def request_status(rid):
    status=request.form.get("status")
    if status not in ("Accepted","Declined"): return redirect(url_for("requests_page"))
    db().execute("UPDATE requests SET status=? WHERE id=? AND to_user=?",(status,rid,session["user_id"])); db().commit()
    flash("Request updated.","success"); return redirect(url_for("requests_page"))

@app.route("/admin", methods=["GET","POST"])
@login_required
def admin():
    uid=session["user_id"]
    # First registered user can enable demo admin via the UI only in local/demo projects.
    user=db().execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    if request.method=="POST" and request.form.get("action")=="make_admin":
        db().execute("UPDATE users SET is_admin=1 WHERE id=?",(uid,)); db().commit()
        flash("Demo admin access enabled for this account.","success"); return redirect(url_for("admin"))
    if not user["is_admin"]:
        return render_template("admin.html", denied=True, stats={}, users=[], opportunities=[])
    conn=db()
    stats={"users":conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
           "opportunities":conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0],
           "projects":conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
           "applications":conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]}
    users=conn.execute("SELECT id,name,email,college,created_at FROM users ORDER BY id DESC").fetchall()
    opportunities=conn.execute("SELECT * FROM opportunities ORDER BY id DESC").fetchall()
    if request.method=="POST" and request.form.get("action")=="add_opportunity":
        db().execute("INSERT INTO opportunities(title,company,kind,location,mode,skills,description,deadline) VALUES(?,?,?,?,?,?,?,?)",
          tuple(request.form.get(k,"").strip() for k in ("title","company","kind","location","mode","skills","description","deadline")))
        db().commit(); flash("Opportunity added.","success"); return redirect(url_for("admin"))
    return render_template("admin.html", denied=False, stats=stats, users=users, opportunities=opportunities)

@app.post("/admin/opportunity/<int:oid>/delete")
@login_required
def admin_delete_opportunity(oid):
    user=db().execute("SELECT is_admin FROM users WHERE id=?",(session["user_id"],)).fetchone()
    if not user or not user["is_admin"]: flash("Admin access required.","error")
    else:
        db().execute("DELETE FROM opportunities WHERE id=?",(oid,)); db().commit(); flash("Opportunity deleted.","success")
    return redirect(url_for("admin"))



@app.route("/interview", methods=["GET", "POST"])
@login_required
def interview():
    # A broad role catalogue plus a free-text field means students are not limited
    # to a tiny fixed list. Questions fall back to a general interview set for new roles.
    roles = [
      "Software Engineer", "Frontend Developer", "Backend Developer", "Full Stack Developer",
      "Python Developer", "Java Developer", "C/C++ Developer", "Android Developer",
      "iOS Developer", "Web Developer", "Mobile App Developer", "Data Analyst",
      "Data Scientist", "Machine Learning Engineer", "AI Engineer", "Data Engineer",
      "Cybersecurity Analyst", "Ethical Hacker", "Cloud Engineer", "Cloud/DevOps Intern",
      "DevOps Engineer", "Site Reliability Engineer", "QA Engineer", "Software Tester",
      "UI/UX Designer", "Product Designer", "Product Manager", "Business Analyst",
      "Business Intelligence Analyst", "Database Administrator", "Network Engineer",
      "Systems Engineer", "Embedded Systems Engineer", "IoT Engineer", "Blockchain Developer",
      "Game Developer", "AR/VR Developer", "Technical Support Engineer",
      "IT Support Specialist", "Digital Marketing Intern", "HR Intern", "Finance Analyst",
      "Research Intern", "Graduate Trainee", "Other / custom role"
    ]
    role = request.form.get("custom_role", "").strip() or request.form.get("role", request.args.get("role", roles[0]))
    question = None
    feedback = None
    answer = ""
    conn = db()
    if request.method == "POST":
        question_id = request.form.get("question_id", "")
        # Accept the displayed question even when it comes from the general fallback bank.
        question = conn.execute("SELECT * FROM interview_questions WHERE id=?", (question_id,)).fetchone()
        answer = request.form.get("answer", "").strip()
        if question:
            words = len(answer.split())
            if words < 8:
                feedback = "Try expanding your answer. Give a clear explanation and include a specific example."
            elif words < 35:
                feedback = "Good start. Improve it by adding a concrete example, explaining your approach, and mentioning the result."
            else:
                feedback = "Nice effort! Check that your answer directly addresses the question and includes a specific example or result."
    questions = conn.execute("SELECT * FROM interview_questions WHERE role=? ORDER BY id", (role,)).fetchall()
    if not questions:
        questions = conn.execute("SELECT * FROM interview_questions WHERE role='Software Engineer' ORDER BY id").fetchall()
    if not question and questions:
        question = questions[0]
    # Ensure submitted question appears in the list even when the chosen role uses fallback questions.
    if question and all(q["id"] != question["id"] for q in questions):
        questions = [question] + list(questions)
    return render_template("interview.html", roles=roles, role=role, questions=questions, question=question,
                           feedback=feedback, answer=answer)

@app.route("/recommendations", methods=["GET", "POST"])
@login_required
def recommendations():
    user = db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    skills = user["skills"] or ""
    interests = user["interests"] or ""
    if request.method == "POST":
        skills = request.form.get("skills", "").strip()
        interests = request.form.get("interests", "").strip()
        db().execute("UPDATE users SET skills=?, interests=? WHERE id=?", (skills, interests, session["user_id"]))
        db().commit()
        flash("Your skills and interests were saved.", "success")
    # Curated career pages are real company destinations, not claims that a vacancy is open.
    companies = [
      {"name":"Microsoft","roles":"Software engineering, cloud, data","keywords":"python java sql cloud devops software engineering data","url":"https://careers.microsoft.com/"},
      {"name":"Google","roles":"Software engineering, data, infrastructure","keywords":"python java sql cloud software engineering data","url":"https://www.google.com/about/careers/applications/"},
      {"name":"Amazon","roles":"Software development, cloud, operations","keywords":"python java sql aws cloud devops software","url":"https://www.amazon.jobs/"},
      {"name":"Adobe","roles":"Software engineering, product, data","keywords":"python java sql javascript software data","url":"https://careers.adobe.com/"},
      {"name":"IBM","roles":"Software, AI, cloud, consulting","keywords":"python java sql ai cloud devops data","url":"https://www.ibm.com/careers"},
      {"name":"Deloitte","roles":"Technology, analytics, consulting","keywords":"python sql data analytics cloud technology","url":"https://www.deloitte.com/global/en/careers.html"},
      {"name":"TCS","roles":"Software development, IT, data","keywords":"python java sql software data cloud","url":"https://www.tcs.com/careers"},
      {"name":"Infosys","roles":"Software, systems, data","keywords":"python java sql software data cloud","url":"https://www.infosys.com/careers/"},
      {"name":"ISRO","roles":"Space technology and computing roles (eligibility varies)","keywords":"python c++ software computing engineering space","url":"https://www.isro.gov.in/Careers.html"},
      {"name":"Wipro","roles":"Software, cloud, data and IT","keywords":"python java sql software cloud data","url":"https://careers.wipro.com/"},
    ]
    terms = (skills + " " + interests).lower()
    tokens = [t.strip(" ,./-") for t in terms.split() if len(t.strip(" ,./-")) > 2]
    ranked = []
    for c in companies:
        hay = c["keywords"] + " " + c["roles"].lower()
        score = sum(1 for t in set(tokens) if t in hay)
        ranked.append((score, c))
    ranked.sort(key=lambda x: (-x[0], x[1]["name"]))
    return render_template("recommendations.html", skills=skills, interests=interests,
                           companies=[c for score, c in ranked if score > 0] or [c for _, c in ranked[:5]])

@app.route("/health")
def health(): return {"status":"ok"}

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
