from sqlalchemy import create_engine
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = create_engine("sqlite:///finance.db")


@app.route("/",methods=["GET", "POST"])
@login_required
def index():
    stocks=[]
    if request.method=="GET":
        username=db.execute("SELECT username, cash FROM users WHERE id=:id",id=session["user_id"]).fetchall()
        List_holdings=db.execute("SELECT ticker,name,sum(number) FROM stocks GROUP BY ticker HAVING username_id=:id",
                                 id=session["user_id"]).fetchall()
        cash=username[0]["cash"]
        stocks_total=0
        index=0
        for stock in List_holdings:
            if stock['sum(number)']>0:
                stocks.append({})
                ticker=stock["ticker"]
                answer=lookup(ticker)
                price=answer["price"]
                total=price*stock["sum(number)"]
                stocks_total+=total
                stocks[index]['ticker']=stock['ticker']
                stocks[index]['name']=stock['name']
                stocks[index]['exchange']=answer['exchange']
                stocks[index]['sum(number)']= stock['sum(number)']
                stocks[index]['price']=price
                stocks[index]['currency']=answer['currency']
                stocks[index]['total']=total
                index+=1
        account_total=cash+stocks_total
        return render_template("index.html",user=username,stocks=stocks,cash=cash,
                               stocks_total=stocks_total,account_total=account_total)
    if request.method=="POST":
        username=db.execute("SELECT username, cash FROM users WHERE id=:id",
                            id=session["user_id"]).fetchall()
        amount=float(request.form["amount"])
        cash_held=db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"]).fetchall()[0]['cash']
        cash=cash_held+amount
        db.execute("UPDATE users SET cash=:cash WHERE id=:id",cash=cash,id=session["user_id"])
        List_holdings=db.execute("SELECT ticker,name,sum(number) FROM stocks GROUP BY ticker HAVING username_id=:id",
                                 id=session["user_id"]).fetchall()
        cash=username[0]["cash"]
        stocks_total=0
        for stock in List_holdings:
            stocks.append({})
            ticker=stock["ticker"]
            price=lookup(ticker)["price"]
            total=price*stock["sum(number)"]
            stocks_total+=total
            stocks[index]['ticker']=stock['ticker']
            stocks[index]['name']=stock['name']
            stocks[index]['sum(number)']= stock['sum(number)']
            stocks[index]['price']=price
            stocks[index]['total']=total
        account_total=cash+stocks_total
        return render_template("index.html",user=username,stocks=stocks,cash=cash,
                               stocks_total=stocks_total,account_total=account_total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock. Display page and inquire about ticker"""
    if request.method=="GET":
        return render_template("buy.html")
    if request.method=="POST":
        ticker=request.form["ticker"]
        exchange=request.form["exchange"]
        if exchange=="":
            exchange="New York"
        stock_price_dict=lookup(ticker,exchange)
        if stock_price_dict['name'] == 'No Data':
            flash('Wrong ticker, stock {} does not exist at exchange {}'.format(ticker,exchange))
            return render_template("buy.html")
        else:
            name=stock_price_dict['name']
            price=stock_price_dict['price']
            return redirect(url_for("buy2",name=name,ticker=ticker,price=price))

@app.route("/buy2", methods=["GET", "POST"])
@login_required
def buy2():
    ticker=request.args.get('ticker')
    name=request.args.get('name')
    price=float(request.args.get('price'))
    if request.method=="GET":
        return render_template("buy2.html",name=name,ticker=ticker,price=price)
    if request.method=="POST":
        try:
            number_of_shares=int(request.form['number'])
        except ValueError:
            flash("must input positive integer number of shares")
            return render_template("buy2.html",name=name,ticker=ticker,price=price)
        if number_of_shares<1:
            flash("must input positive integer number of shares")
            return render_template("buy2.html",name=name,ticker=ticker,price=price)
        else:
            funds_available=db.execute("SELECT cash FROM users WHERE id=:id",
                                       id=session["user_id"]).fetchall()[0]['cash']
            funds_needed=price*number_of_shares

            if funds_needed>funds_available:
                flash("too many number of shares cannot aford more than {}".format(round(funds_available/price,0)))
                return render_template("buy2.html",name=name,ticker=ticker,price=price)
            else:
                number_of_shares_held=db.execute("SELECT sum(number) FROM stocks WHERE username_id=:id AND ticker=:ticker",
                                                 id=session["user_id"],ticker=ticker).fetchall()[0]['sum(number)']
                if number_of_shares_held==None:
                    number_of_shares_held=0
                number_held=number_of_shares_held+number_of_shares
                funds_left=funds_available-funds_needed
                db.execute("INSERT INTO stocks(username_id,ticker,name,number,price,amount,number_held) VALUES (:username,:ticker,:name,:number,:price,:amount,:number_held)",username=session["user_id"],ticker=ticker,name=name,number=number_of_shares,price=price,amount=funds_needed,number_held=number_held)
                db.execute("UPDATE users SET cash=:cash WHERE id=:id",
                           cash=funds_left,id=session["user_id"])


                return render_template("bought.html",name=name,price=price,
                                       number=number_of_shares,amount=funds_needed,
                                       funds=funds_left,number_held=number_held,
                                       ticker=ticker)

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    stocks=[]
    username=db.execute("SELECT username FROM users WHERE id=:id",
                        id=session["user_id"]).fetchall()[0]["username"]
    List_holdings=db.execute("SELECT ticker,name,number,price,timestamp FROM stocks WHERE username_id=:id",
                             id=session["user_id"]).fetchall()
    for index,transaction in enumerate(List_holdings):
        stocks.append({})
        stocks[index]['ticker']=transaction['ticker']
        stocks[index]['name']=transaction['name']
        stocks[index]['number']=transaction['number']
        stocks[index]['price']=transaction['price']
        stocks[index]['timestamp']=transaction['timestamp']
        if transaction["number"]>0:
            stocks[index]["side"]="BUY"
        elif transaction["number"]<0:
            stocks[index]["side"]="SELL"

    return render_template("history.html",stocks=stocks,user=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()
    rows=db.execute("SELECT username FROM users").fetchall()
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return render_template("login.html",users=rows)

        # ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return render_template("login.html",users=rows)

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", 
                            username=request.form.get("username")).fetchall()
        
		

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            flash("invalid username and/or password")
            return render_template("login.html",users=rows)

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html",users=rows)

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method=='GET':
        stock_price_dict={"name": "","price":"","currency":"","exchange":"","symbol":""}
        return render_template('quote.html',stock=stock_price_dict)

    elif request.method=='POST':
        ticker=request.form["ticker"]
        exchange=request.form["exchange"]
        if ticker=="":
            flash ("No ticker given.")
            stock_price_dict={"name": "","price":"","currency":"","exchange":"","symbol":""}
            return render_template('quote.html',stock=stock_price_dict)
        if exchange=="":
            flash ("No exchange given, assumed New York.")
            exchange='New York'
        stock_price_dict=lookup(ticker,exchange)
        if stock_price_dict['name']=='No Data':
            flash("Ticker not recognized.")
        return render_template('quote.html',stock=stock_price_dict)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        rows = db.execute("SELECT username FROM users").fetchall()
        # ensure username was submitted
        if request.form["username"]=='':
            flash("must provide username")
            return render_template("register.html")
        elif request.form["username"] in rows:
            flash("user already exists")
            return render_template("register.html")
        # ensure password was submitted
        elif request.form["password"]=='':
            flash("must provide password")
            return render_template("register.html")

        # insert to database

        db.execute("INSERT INTO users (username,hash) VALUES (:username, :phash)", 
                   username=request.form["username"], phash=pwd_context.hash(request.form["password"]))
        return render_template("login.html")
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    stock_price_dict={"name": "","price":"","currency":"","exchange":"","symbol":""}
    list_of_stocks_held=db.execute("SELECT DISTINCT name,ticker FROM stocks WHERE username_id=:id",
                                                 id=session["user_id"]).fetchall()
    if request.method=="GET":
        return render_template("sell.html",stocks=list_of_stocks_held,stock=stock_price_dict)
    elif request.method=="POST":
        ticker=request.form["ticker"]
        try:
            number_of_shares_held=int(db.execute("SELECT sum(number) FROM stocks WHERE username_id=:id AND ticker=:ticker",
                                                 id=session["user_id"],ticker=ticker).fetchall()[0]['sum(number)'])
        except:
            flash("No stocks held in account")
            return render_template("sell.html",stocks=list_of_stocks_held)
        if number_of_shares_held<1:
            flash("Not enough stocks held in account")
            return render_template("sell.html",stocks=list_of_stocks_held)
        stock_price_dict=lookup(ticker)
        if stock_price_dict == None:
            return apology("Stock doesn't have a price")
        else:
            name=stock_price_dict['name']
            price=stock_price_dict['price']
            return redirect(url_for("sell2",name=name,ticker=ticker,price=price,
                                    nos=number_of_shares_held))

@app.route("/sell2", methods=["GET", "POST"])
@login_required
def sell2():
    ticker=request.args.get('ticker')
    name=request.args.get('name')
    price=float(request.args.get('price'))
    number_of_shares_held=int(request.args.get('nos'))
    if request.method=="GET":
        return render_template("sell2.html",name=name,ticker=ticker,
                               price=price,nos=number_of_shares_held)
    if request.method=="POST":
        try:
            number_of_shares=int(request.form['number'])
        except ValueError:
            return apology("must input positive integer number of shares")
        if number_of_shares<1:
            return apology("must input positive integer number of shares")
        else:
            funds_available=db.execute("SELECT cash FROM users WHERE id=:id",
                                       id=session["user_id"]).fetchall()[0]['cash']
            cash_proceeds=price*number_of_shares
            if number_of_shares_held<number_of_shares:
                return apology("you do not have that many shares")


            else:
                number_held=number_of_shares_held-number_of_shares
                funds_left=funds_available+cash_proceeds
                db.execute("INSERT INTO stocks(username_id,ticker,name,number,price,amount,number_held) VALUES (:username,:ticker,:name,:number,:price,:amount,:number_held)",username=session["user_id"],
                           ticker=ticker,name=name,number=-number_of_shares,
                           price=price,amount=cash_proceeds,number_held=number_held)
                db.execute("UPDATE users SET cash=:cash WHERE id=:id",
                           cash=funds_left,id=session["user_id"])


                return render_template("sold.html",name=name,price=price,
                                       number=-number_of_shares,amount=cash_proceeds,
                                       funds=funds_left,number_held=number_held,
                                       ticker=ticker)