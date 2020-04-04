import os

from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
import json

app = Flask(__name__)

# Goodreads API
key = "bnpml9jlJWMXk0Y2tEOYBQ"
# secret: fs6tUrIfRMTrgrajHQJWaMfjX1G7TRF4f0Rmj9Ldlo4

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
	if session.get("loggedin") is None:
		session["loggedin"] = None
	return render_template("index.html")
	
@app.route("/register", methods=["POST", "GET"])
def register():
	if request.method == "GET":
		return render_template("register.html")
	else:
		username = request.form.get("username")
		password = request.form.get("password")
		try:
			db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
				{"username": username, "password": password})
			db.commit()
		except:
			return redirect(url_for('error_page'))
		return redirect("/")

@app.route("/login", methods=["POST", "GET"])
def login():
	if request.method == "GET":
		return render_template("login.html")
	else:
		username = request.form.get("username")
		password = request.form.get("password")
		user = db.execute("SELECT * FROM users WHERE username = :username AND password = :password",
			{"username": username, "password": password}).fetchone()
		print(user)
		if user:
			session["loggedin"] = {"id": user[0], "username": user[1]}
		return redirect("/")

@app.route("/search", methods=["POST", "GET"])
def search():
	if session["loggedin"] == None:
		return redirect(url_for("error_page"))

	if request.method == "POST":
		keyword = request.form.get("search")
		books = db.execute("SELECT * FROM books WHERE isbn LIKE :keyword OR lower(title) LIKE :keyword OR lower(author) LIKE :keyword;",
		{"keyword": '%'+keyword+'%'}).fetchall()
		return render_template("search.html", books=books)
	else:
		return render_template("search.html")
		

@app.route("/book/<string:book_id>")
def book_page(book_id):
	if session["loggedin"] == None:
		return redirect(url_for("error_page"))
	book = db.execute("SELECT * FROM books WHERE id = :id",
			{"id": book_id}).fetchone()
	book_ratings = db.execute("SELECT COUNT(*), ROUND(AVG(rating),1) FROM book_reviews WHERE book_id = :book_id",
			{"book_id": book_id}).fetchone()
	book_details = {"book_id": book[0],
					"isbn": book[1],
					"title": book[2],
					"author": book[3],
					"year": book[4],
					"ratings_count": book_ratings[0],
					"average_rating": book_ratings[1]
					}
	reviews = db.execute("SELECT users.username, message, rating FROM book_reviews JOIN users ON book_reviews.user_id = users.id WHERE book_id = :book_id;",
			{"book_id": book_id}).fetchall()
	# Get Goodreads Data
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": book_details["isbn"]})
	res_dict = json.loads(res.text)
	goodreads_book_details = res_dict['books'][0]

	return render_template("book_page.html", book_details=book_details, reviews=reviews, goodreads_book_details=goodreads_book_details)

@app.route("/book/<string:book_id>/review", methods=["POST", "GET"])
def book_review(book_id):
	if session["loggedin"] == None:
		return redirect(url_for("error_page"))

	if request.method == "POST":
		message = request.form.get("message")
		rating = request.form.get("rating")
		user = session["loggedin"]["id"]
		try:
			same_user_check = db.execute("SELECT user_id FROM book_reviews WHERE user_id = :user AND book_id = :book_id;",
				{"user": user, "book_id": book_id}).fetchone()
			if same_user_check != None:
				raise Exception("You have already reviewed!")

			db.execute("INSERT INTO book_reviews (book_id, user_id, message, rating) VALUES (:book_id, :user_id, :message, :rating)",
				{"book_id": book_id, "user_id": user, "message": message, "rating": rating})
			db.commit()
		except:
			return redirect(url_for('error_page'))
	return redirect("/book/"+book_id)

@app.route("/api/<string:isbn>")
def get_api(isbn):
	if session["loggedin"] == None:
		return redirect(url_for("error_page"))

	book = db.execute("SELECT * FROM books WHERE isbn = :isbn",
			{"isbn": isbn}).fetchone()
	if book == None:
		return redirect(url_for('error_page'))
	book_ratings = db.execute("SELECT COUNT(*), ROUND(AVG(rating),1) FROM book_reviews WHERE book_id = :book_id",
			{"book_id": book[0]}).fetchone()
	book_details = {"title": book[1],
					"author": book[2],
					"year": book[3],
					"isbn": book[4],
					"ratings_count": int(book_ratings[0]),
					"average_rating": float(book_ratings[1])
					}
	return json.dumps(book_details)

@app.route
@app.route("/logout")
def logout():
	session["loggedin"] = None
	return redirect("/")

@app.route("/error")
def error_page():
	return render_template("error.html")


# if session.get("loggedin") is None:
#   		session["loggedin"] = None
# 	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": "000723368X"})
# 	return res.json()

# res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": book_details["isbn"]})
# book_additional_details = json.loads(res.text)
# rating = book_additional_details['books'][0]['average_rating']