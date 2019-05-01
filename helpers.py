import urllib.request
from bs4 import *
import re
import quandl
from flask import redirect, render_template, request, session, url_for
from functools import wraps

def apology(top="", bottom=""):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
            ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return top+bottom

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def lookup(symbol,exchange='New York'):
    """Look up quote for symbol."""
    exchange_dict={"New York":":US",
                   "London":":LN",
                   "Frankfurt":":GR",
                   "Milan":":IM",
                   "Paris":":FP",
                   "Tokyo":":JP",
                   "Warsaw":"WSE/"}
    # reject symbol if it starts with caret
    if symbol.startswith("^"):
        return {
        "name": "No Data",
        "price": 0,
        "currency":"No Data",
        "exchange":"No Data",
        "symbol": symbol.upper()}

    # reject symbol if it contains comma
    if "," in symbol:
        return {
        "name": "No Data",
        "price": 0,
        "currency":"No Data",
        "exchange":"No Data",
        "symbol": symbol.upper()}
    if exchange=='Warsaw':
        try:
            ticker=exchange_dict[exchange]+symbol
            quandl_api_key='bLpE4MsFSUQPvssWNg79'
            quandl.ApiConfig.api_key=quandl_api_key
            answer=quandl.get(ticker,rows=1,column_index=4)
            name=symbol
            priceStr=answer['Close'].iloc[0]
            currency='PLN'
            exchange='GPW'
            companyId=ticker           
        except:
            return{
                "name": "No Data",
                "price": 0,
                "currency":"No Data",
                "exchange":"No Data",
                "symbol": ticker.upper()}
        
    else:
        # Assume symbol in US if not : given
        ticker = symbol +exchange_dict[exchange]
        # query Bloomberg for quote for US London and Europe
        try:
            url = "https://www.bloomberg.com/quote/{}".format(ticker)
            req=urllib.request.Request(url,headers={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.1"})
            html=urllib.request.urlopen(req).read().decode('utf-8')
            soup=BeautifulSoup(html,'html.parser')
            priceStr=soup.body.find_all(class_=re.compile("priceText"))[0].string
            name=soup.body.find_all(class_=re.compile("companyName"))[0].string
            currency=soup.body.find_all(class_=re.compile("currency"))[0].string
            exchange=soup.body.find_all(class_=re.compile("exchange"))[0].string
            companyId=soup.body.find_all(class_=re.compile("companyId"))[0].string
        except:
            return{
            "name": "No Data",
            "price": 0,
            "currency":"No Data",
            "exchange":"No Data",
            "symbol": ticker.upper()}
        # query quandl for Warsaw
        # ensure stock exists
    try:
        price = float(priceStr)
    except:
        return{
        "name": "No Data",
        "price": 0,
        "currency":"No Data",
        "exchange":"No Data",
        "symbol": symbol.upper()}

    # return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
    return {
        "name": name,
        "price": price,
        "currency":currency,
        "symbol": companyId,
        "exchange":exchange
    }

def usd(value):
    """Formats value as USD."""
    return "${:,.2f}".format(value)
