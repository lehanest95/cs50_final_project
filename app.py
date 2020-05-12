import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

import datetime

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
os.environ["API_KEY"] = "pk_0923fa0d402b45abbde2964318ebdd08"
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    # get table with amount of each stock in portfolio
    portfolio = db.execute(
        "SELECT symbol, SUM(amount) amount FROM history WHERE user_id=:user_id GROUP BY symbol HAVING SUM(amount) > 0",
        user_id=user_id)

    current_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=user_id)[0]["cash"]
    portfolio_value = current_cash

    # adding new key to dictionary with corresponding value
    for row in range(len(portfolio)):
        symbol = portfolio[row]["symbol"]
        lookup_arr = lookup(symbol)  # to optimize query to API
        price = lookup_arr["price"]
        portfolio[row]["name"] = lookup_arr["name"]
        portfolio[row]["price"] = usd(price)
        portfolio[row]["sum"] = round(price * portfolio[row]["amount"], 2)
        portfolio_value += portfolio[row]["sum"]
        portfolio[row]["sum"] = usd(portfolio[row]["sum"])

    return render_template("index.html", portfolio=portfolio, cash=usd(round(current_cash, 2)),
                           portfolio_value=usd(round(portfolio_value, 2)))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not lookup(symbol):
            return apology("the symbol does not exist", 403)
        price = lookup(symbol)["price"]

        amount = int(request.form.get("shares"))
        if amount < 1:
            return apology("amount is not a positive integer", 403)

        now = datetime.datetime.now()
        user_id = session["user_id"]

        transaction_amount = price * amount
        current_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=user_id)
        current_cash = current_cash[0]["cash"]
        cash_after = current_cash - transaction_amount

        if cash_after < 0:
            return apology("not enough cash to make the purchase", 403)

        # update history table
        db.execute(
            "INSERT INTO history (user_id, symbol, amount, price, datetime) VALUES (:user_id, :symbol, :amount, :price, :datetime)",
            user_id=user_id, symbol=symbol, amount=amount, price=price, datetime=now)

        # update user table with new cash amount
        db.execute("UPDATE users SET cash = :cash_after WHERE id = :user_id", cash_after=cash_after, user_id=user_id)

        flash("Stock(s) bought")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    history = db.execute("SELECT * FROM history WHERE user_id=:user_id", user_id=user_id)

    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

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

        # Redirect user to home page

        flash("Logged in")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        symbol = request.form.get("symbol")

        # lookup return a dictionary with 3 values
        quoted = lookup(symbol)

        # check if user typed the existing symbol
        if not quoted:
            return render_template("quoted.html", quoted="You typed incorrect symbol")

        # A share of Apple, Inc. (AAPL) costs $310.13.
        display_text = "A share of " + quoted["name"] + " (" + symbol + ") costs $" + str(quoted["price"])

        # Redirect user to home page
        return render_template("quoted.html", quoted=display_text)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
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


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]

    # get table with amount of each stock in portfolio
    portfolio = db.execute(
        "SELECT DISTINCT symbol FROM history WHERE user_id=:user_id GROUP BY symbol HAVING SUM(amount) > 0",
        user_id=user_id)

    if request.method == "POST":
        symbol = request.form.get("symbol")
        # if symbol not in portfolio["symbol"]:
        #     return apology("little Gangsta hacker", 403)
        amount = int(request.form.get("shares"))
        if amount < 1:
            return apology("you can't sell negative amounth of shares")

        # get selected symbol amount in portfolio
        symbol_amount = \
        db.execute("SELECT SUM(amount) amount FROM history WHERE user_id=:user_id AND symbol=:symbol", user_id=user_id,
                   symbol=symbol)[0]["amount"]
        if amount > symbol_amount:
            return apology("you're trying to sell more stocks than you own", 403)

        # calculate transaction sum
        price = float(lookup(symbol)["price"])
        sell_sum = price * amount
        current_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=user_id)[0]["cash"]
        cash_result = current_cash + sell_sum

        # update cash amount
        db.execute("UPDATE users SET cash = :cash_result WHERE id=:user_id", cash_result=cash_result, user_id=user_id)

        # update history table
        now = datetime.datetime.now()
        db.execute(
            "INSERT INTO history (user_id, symbol, amount, price, datetime) VALUES (:user_id, :symbol, :amount, :price, :datetime)",
            user_id=user_id, symbol=symbol, amount=-amount, price=price, datetime=now)

        # Redirect user to home page
        flash("Stock sold")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", portfolio=portfolio)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        user_id = session["user_id"]
        new_password = request.form.get("password")
        new_password_again = request.form.get("password_again")
        if new_password != new_password_again:
            return apology("Come on, new passwords don't match", 403)

        # check whether password is the same as current
        old_hash = db.execute("SELECT hash FROM users WHERE id=:user_id", user_id=user_id)[0]["hash"]
        if check_password_hash(old_hash, new_password):
            return apology("I think you wanted to change pass =/, but it's the same as previous", 403)

        # write new password to DB
        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash=:new_hash WHERE id=:user_id", new_hash=new_hash, user_id=user_id)

        # Redirect user to home page
        flash("Password changed")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change-password.html")

# export API_KEY=pk_0923fa0d402b45abbde2964318ebdd08
