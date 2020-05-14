import itertools
import json
import os
import sqlite3

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from itertools import starmap

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
db_file = "final.db"
db = SQL("sqlite:///" + db_file)

# session["user_id"]
# getting local dicts to optimize for SQL queries
problems = db.execute("SELECT * FROM problems")
weeks = db.execute("SELECT * FROM problem_week")
questions = db.execute("SELECT * FROM questions")

# getting data from merged.db for fancy stats
# https://stackoverflow.com/questions/17038193/select-row-with-most-recent-date-per-user
# first
#     SELECT
#     t1. *
#     FROM
#     merged
#     t1
#     WHERE
#     t1.Date = (SELECT MIN(t2.Date)
#     FROM
#     merged
#     t2
#     WHERE
#     t2.AuthorID = t1.AuthorID)
first_topic = 0


@app.route("/")
def index():
    # check for GOD MODE
    if session.get("user_id") is not None:
        if session.get("god_mode") == "god":
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
    user_data = db.execute("SELECT * FROM users WHERE id=:user_id", user_id=session["user_id"])
    participated_status = user_data[0]["participated"]

    if request.method == "POST":
        boiling_point = 511  # https://www.youtube.com/watch?v=PcQtdjlxp0M FRIENDS: Boiling Point Of Brain (S05 E11)
        now = datetime.now()

        # getting answers to every question
        for row in questions:
            question_id = str(row["id"])
            answer = request.form.get(question_id)
            if answer == "Open this select menu":
                answer = None
            # checking for GOD MODE
            if row["answer_type"] == "positive_int":
                if not answer:
                    answer = None
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

            # if user didn't participate before
            if participated_status != "yes":
                db.execute(
                    "INSERT INTO answers(user_id, question_id, answer, answer_date) VALUES(:user_id, :question_id, :answer, :answer_date)",
                    user_id=session["user_id"], question_id=question_id, answer=answer, answer_date=now)
            # if yes - we just update already submitted answers
            else:
                db.execute(
                    "UPDATE answers SET answer=:answer, answer_date=:now WHERE user_id=:user_id AND question_id=:question_id"
                    , question_id=question_id, answer=answer, now=now, user_id=session["user_id"])

        # update status of the user (participated)
        db.execute("UPDATE users SET participated=:participated WHERE id=:user_id", participated="yes",
                   user_id=session["user_id"])
        flash("Submitted! Now check stats!")
        return redirect("/statistics")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        user_id = session["user_id"]
        answers = db.execute(
            "SELECT questions.question_name, answers.answer, answers.answer_date FROM questions JOIN answers ON questions.id=answers.question_id JOIN users ON answers.user_id=users.id WHERE users.id=:user_id",
            user_id=session["user_id"])
        return render_template("participate.html", user_id=user_id, problems=problems, weeks=weeks,
                               questions=questions, participated_status=participated_status, answers=answers)


@app.route("/statistics")
def statistics():
    """Show history of transactions"""
    # if session.user_id:

    # get current counters for main page
    users_counter = db.execute("SELECT MAX(id) FROM users")[0]["MAX(id)"]
    answers_counter = db.execute("SELECT MAX(answer_id) FROM answers")[0]["MAX(answer_id)"]
    users_participated = db.execute('SELECT count(id) FROM users WHERE participated = "yes"')[0]["count(id)"]
    # data = db.execute("SELECT id, problem_week FROM problems GROUP BY problem_week")

    # using different connector to have proper array structure
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # data for "select_week"
    cur.execute('SELECT "Week #" || problem_week.week_number || " " || "(" || problem_week.week_topic || ")" AS week, COUNT(answers.answer) AS votes FROM answers answers, questions questions, problem_week problem_week WHERE answers.question_id = questions.id AND answers.answer = problem_week.week_number AND questions.answer_type = "select_week" GROUP BY answers.answer')
    week_data = cur.fetchall()
    week_chart = {"chart":
                 {"container": "week_container",
                  "series": [
                      {"enabled": True,
                       "seriesType": "bar",
                       "data": week_data
                       }],
                  "title": "Results by week",
                  "type": "bar"}}

    # data for "select_problem_set"
    cur.execute('SELECT "(Week #"|| problems.problem_week || ") " || problems.problem_name AS pset, COUNT(answers.answer) AS counter FROM answers answers, questions questions, problems problems WHERE answers.question_id = questions.id AND answers.answer = problems.id AND questions.answer_type = "select_problem_set" GROUP BY problems.problem_name ORDER BY problems.id')
    pset_data = cur.fetchall()
    pset_chart = {"chart":
                      {"container": "pset_container",
                       "series": [
                           {"enabled": True,
                            "seriesType": "bar",
                            "data": pset_data
                            }],
                       "title": "Results by pset",
                       "type": "bar"}}

    # data for "select_bool"
    cur.execute(
        'SELECT answers.answer AS answer, COUNT(answers.answer_id) as counter FROM answers answers, questions questions WHERE answers.question_id = questions.id AND questions.answer_type = "select_bool" GROUP BY answers.answer')
    bool_data = cur.fetchall()
    bool_chart = {"chart":
                      {"container": "bool_container",
                       "data": bool_data,
                       "title": "Results by yes/no",
                       "type": "pie"}}

    # data for "positive_int"
    cur.execute(
        'SELECT answers.answer, COUNT(answers.answer_id) as counter  FROM answers answers, questions questions WHERE answers.question_id = questions.id AND questions.answer_type = "positive_int" GROUP BY answers.answer')
    int_data = cur.fetchall()
    int_chart = {"chart":
                      {"container": "int_container",
                       "series": [
                           {"enabled": True,
                            "seriesType": "spline",
                            "data": int_data
                            }],
                       "title": "Results by int",
                       "type": "line"}}

    return render_template("statistics.html", users_counter=users_counter, answers_counter=answers_counter,
                           users_participated=users_participated, questions=questions, problems=problems, weeks=weeks,
                           weekData=json.dumps(week_chart), psetData=json.dumps(pset_chart),
                           boolData=json.dumps(bool_chart), intData=json.dumps(int_chart), first_topic=first_topic)


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
        register_date = datetime.now()
        username = request.form.get("username")
        password_hashed = generate_password_hash(request.form.get("password_again"))
        db.execute(
            "INSERT INTO users (username, hash, register_date) VALUES (:username, :password_hashed, :register_date)",
            username=username,
            password_hashed=password_hashed, register_date=register_date)

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
