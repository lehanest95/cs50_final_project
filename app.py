import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///final.db")


# session["user_id"]

@app.route("/")
def index():
    # check for GOD MODE
    if session.get("user_id") is not None:
        if session["god_mode"] == "god":
            flash("GOD MODE!")

    # get current counters for main page
    users_counter = db.execute("SELECT MAX(id) FROM users")[0]["MAX(id)"]
    answers_counter = db.execute("SELECT MAX(answer_id) FROM answers")[0]["MAX(answer_id)"]
    users_participated = db.execute('SELECT count(id) FROM users WHERE participated = "yes"')[0]["count(id)"]
    return render_template("index.html", users_counter=users_counter, answers_counter=answers_counter,
                           users_participated=users_participated)


@app.route("/participate", methods=["GET", "POST"])
@login_required
def participate():
    # getting local dicts to optimize for SQL queries
    problems = db.execute("SELECT * FROM problems")
    weeks = db.execute("SELECT * FROM problem_week")
    questions = db.execute("SELECT * FROM questions")

    if request.method == "POST":
        boiling_point = 511  # https://www.youtube.com/watch?v=PcQtdjlxp0M FRIENDS: Boiling Point Of Brain (S05 E11)

        # getting answers to every question
        for row in questions:
            question_id = str(row["id"])
            answer = request.form.get(question_id)

            # checking for GOD MODE
            if row["answer_type"] == "positive_int":
                if not answer:
                    answer = 0
                elif int(answer) == boiling_point:
                    # turn on GOD MODE
                    flash("YOU ARE THE GOD OF CONSPIRACY AND HACKING, CONGRATS!")
                    db.execute("UPDATE users SET god_mode=:god_value WHERE id=:user_id", god_value="god",
                               user_id=session["user_id"])
                    session["god_mode"] = "god"
                elif int(answer) != boiling_point:
                    # disable God Mode
                    db.execute("UPDATE users SET god_mode=:god_value WHERE id=:user_id", god_value="",
                               user_id=session["user_id"])
                    session["god_mode"] = ""

            db.execute("INSERT INTO answers(user_id, question_id, answer) VALUES(:user_id, :question_id, :answer)",
                       user_id=session["user_id"], question_id=question_id, answer=answer)

        # update status of the user (participated)
        db.execute("UPDATE users SET participated=:participated WHERE id=:user_id", participated="yes", user_id=session["user_id"])
        flash("Submitted! Now check stats!")
        return redirect("/statistics")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        user_id = session["user_id"]
        return render_template("participate.html", user_id=user_id, problems=problems, weeks=weeks,
                               questions=questions)


@app.route("/statistics")
def statistics():
    """Show history of transactions"""
    # if session.user_id:

    # user_id = session["user_id"]
    return render_template("statistics.html")


@app.route("/about")
@login_required
def about():
    return render_template("about.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        if rows[0]["god_mode"] == "god":
            session["god_mode"] = "god"
        else:
            session["god_mode"] = ""

        # Redirect user to home page

        flash("Logged in")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to home page
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password (again) was submitted
        elif not request.form.get("password_again"):
            return apology("must provide password (again)", 403)

        if request.form.get("password") != request.form.get("password_again"):
            return apology("passwords must match!", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username isn't already taken
        if len(rows) == 1:
            return apology("username already taken", 403)

        # add user to the database
        username = request.form.get("username")
        password_hashed = generate_password_hash(request.form.get("password_again"))
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hashed)", username=username,
                   password_hashed=password_hashed)

        # get user id from the database
        rows = db.execute("SELECT id FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page

        flash("Registered and logged in")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    return apology("TODO")


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        new_password = request.form.get("password")
        new_password_again = request.form.get("password_again")
        if new_password != new_password_again:
            return apology("Come on, new passwords don't match", 403)

        # check whether password is the same as current
        old_hash = db.execute("SELECT hash FROM users WHERE id=:user_id", user_id=session["user_id"])[0]["hash"]
        if check_password_hash(old_hash, new_password):
            return apology("I think you wanted to change pass =/, but it's the same as previous", 403)

        # write new password to DB
        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash=:new_hash WHERE id=:user_id", new_hash=new_hash, user_id=session["user_id"])

        # Redirect user to home page
        flash("Password changed")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change-password.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
