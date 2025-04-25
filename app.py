from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from models import User, Admin, Reader
import pymysql
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL Connection
def get_mysql_connection():
    return pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='1234',
        db='libritxt2',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# MongoDB Connection
mongo_client = MongoClient('mongodb://localhost:27016/')
mongo_db = mongo_client['biblioteca']
coments_collection = mongo_db['comentaris']
historial_collection = mongo_db['historial_prestecs']
text_collection = mongo_db['text_llibre']

def load_users():
    users = {}
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, nom, email, pass, tipus FROM usuaris"
            cursor.execute(sql)
            results = cursor.fetchall()
            
            for user_data in results:
                user_id = user_data['id']
                username = user_data['nom']
                email = user_data['email']
                password = user_data['pass']
                role = user_data['tipus']
                
                if role == 'admin':
                    user = Admin(user_id, username, password)
                else:
                    user = Reader(user_id, username, password)
                users[username] = user
    finally:
        conn.close()
    return users

# Load users at startup
users = load_users()

def get_all_books():
    books = []
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, titol, autor, categoria, any_publicacio FROM llibres"
            cursor.execute(sql)
            results = cursor.fetchall()

            for book_data in results:
                book_isbn = book_data['id']
                title = book_data['titol']
                author = book_data['autor']
                category = book_data['categoria']
                publication_year = book_data['any_publicacio']

                categories = []
                if category:
                    categories = category.split(',')

                cover_image = f"cover{book_isbn}.jpg"
                cover_url = f"{cover_image}"
                description = text_collection.find_one({'llibre_id': book_isbn - 1})
                description_text = description['text'] if description else None

                books.append({
                    'isbn': book_isbn,
                    'name': title,
                    'author': author,
                    'categories': categories,
                    'editorial': None,  # Placeholder for editorial
                    'release_year': publication_year,
                    'cover': cover_url,
                    'description': description_text
                })
    finally:
        conn.close()
    return books

# Get Categories
def get_all_categories(books):
    categories = set()
    for book in books:
        for category in book['categories']:
            categories.add(category.strip())
    return sorted(categories)

# Check lending status of a book
def get_lending_status(isbn):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            # Join with users table to get username directly
            sql = """
                SELECT u.nom as username 
                FROM prestecs p
                JOIN usuaris u ON p.usuari_id = u.id
                WHERE p.llibre_id = %s AND p.data_retorn IS NULL
            """
            cursor.execute(sql, (isbn,))
            result = cursor.fetchone()
            if result:
                return result['username']
    except pymysql.MySQLError as e:
        print(f"Error checking lending status: {e}")
    finally:
        conn.close()
    return None

## START AQUI ##########################################
# Lend a book to a user
def lend_book(isbn, username):
    conn = get_mysql_connection()
    try:
        # First get the user_id based on username
        with conn.cursor() as cursor:
            sql = "SELECT id FROM usuaris WHERE nom = %s"
            cursor.execute(sql, (username,))
            user_result = cursor.fetchone()
            
            if not user_result:
                return False
            
            user_id = user_result['id']
            
            # Insert the lending record
            sql = """
                INSERT INTO prestecs 
                (llibre_id, usuari_id, data_prestec, data_retorn) 
                VALUES (%s, %s, NOW(), NULL)
            """
            cursor.execute(sql, (isbn, user_id))
            conn.commit()
            return True
    except pymysql.MySQLError as e:
        print(f"Error lending book: {e}")
        return False
    finally:
        conn.close()

# Return a book
def return_book(isbn):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            # Update the return date instead of deleting the record
            sql = """
                UPDATE prestecs 
                SET data_retorn = NOW()
                WHERE llibre_id = %s AND data_retorn IS NULL
            """
            cursor.execute(sql, (isbn,))
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    except pymysql.MySQLError as e:
        print(f"Error returning book: {e}")
        return False
    finally:
        conn.close()

@app.route('/')
def index():
    if 'usuari' not in session:
        return redirect(url_for('login'))

    sort = request.args.get('sort', 'default')

    selected_category = request.args.get('category', None)

    books = get_all_books()

    filtered_books = books.copy()
    if selected_category:
        filtered_books = [book for book in filtered_books if selected_category in book['categories']]

    # Order
    if sort == 'name_asc':
        filtered_books.sort(key=lambda x: x['name'].lower())
    elif sort == 'name_desc':
        filtered_books.sort(key=lambda x: x['name'].lower(), reverse=True)

    all_categories = get_all_categories(books)

    return render_template(
        'index.html',
        usuari=session['usuari'],
        books=filtered_books,
        sort=sort,
        all_categories=all_categories,
        selected_category=selected_category
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuari = request.form['usuari']
        contrasenya = request.form['contrasenya']
        
        if usuari in users and users[usuari].check_password(contrasenya):
            session['usuari'] = usuari
            session['role'] = users[usuari].role
            flash('Login correcte!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuari o contrasenya incorrectes', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuari', None)
    session.pop('role', None)
    flash('Has tancat sessió correctament.', 'success')
    return redirect(url_for('index'))

def get_book_by_isbn(isbn):
    with open('data/books.txt', 'r', encoding='utf-8') as f:
        for line in f:
            fields = line.strip().split('|')
            if len(fields) == 8 and fields[0] == isbn:
                categories = fields[3].split(',') if fields[3] else []
                return {
                    'isbn': fields[0],
                    'name': fields[1],
                    'author': fields[2],
                    'categories': categories,
                    'editorial': fields[4],
                    'release_year': fields[5],
                    'cover': fields[6],
                    'description': fields[7]
                }
    return None

def get_reviews_by_isbn(isbn):
    reviews = []
    try:
        with open('data/reviews.txt', 'r', encoding='utf-8') as f:
            for line in f:
                fields = line.strip().split('|')
                if fields[0] == isbn:
                    review_type = fields[1]
                    if review_type == 'numeric':
                        reviews.append({
                            'type': 'numeric',
                            'user': fields[2],
                            'timestamp': fields[3],
                            'rating': int(fields[4])
                        })
                    elif review_type == 'comment':
                        reviews.append({
                            'type': 'comment',
                            'user': fields[2],
                            'timestamp': fields[3],
                            'comment': fields[4]
                        })
                    elif review_type == 'recommendation':
                        recommendation = fields[4].lower() == 'yes'
                        reviews.append({
                            'type': 'recommendation',
                            'user': fields[2],
                            'timestamp': fields[3],
                            'recommendation': recommendation
                        })
    except FileNotFoundError:
        pass
    return reviews

@app.route('/book/<isbn>')
def book_details(isbn):
    book = get_book_by_isbn(isbn)
    if not book:
        return "Book not found", 404
    reviews = get_reviews_by_isbn(isbn)
    numeric_reviews = [review['rating'] for review in reviews if review['type'] == 'numeric']
    average_rating = sum(numeric_reviews) / len(numeric_reviews) if numeric_reviews else 0
    recommendation_reviews = [review['recommendation'] for review in reviews if review['type'] == 'recommendation']
    recommendation_percentage = (sum(recommendation_reviews) / len(recommendation_reviews) * 100) if recommendation_reviews else 0
    borrower = get_lending_status(isbn)
    return render_template(
        'book.html',
        book=book,
        reviews=reviews,
        average_rating=average_rating,
        recommendation_percentage=recommendation_percentage,
        borrower=borrower,
        usuari=session.get('usuari')
    )

@app.route('/lend/<isbn>', methods=['POST'])
def lend(isbn):
    if 'usuari' not in session:
        flash('Cal iniciar sessió per prestar un llibre.', 'error')
        return redirect(url_for('login'))
    user = session['usuari']
    borrower = get_lending_status(isbn)
    if borrower:
        flash('Aquest llibre ja està prestat.', 'error')
    else:
        lend_book(isbn, user)
        flash('Llibre prestat amb èxit!', 'success')
    return redirect(url_for('book_details', isbn=isbn))

@app.route('/return/<isbn>', methods=['POST'])
def return_book_route(isbn):
    if 'usuari' not in session:
        flash('Cal iniciar sessió per tornar un llibre.', 'error')
        return redirect(url_for('login'))
    user = session['usuari']
    borrower = get_lending_status(isbn)
    if borrower == user:
        return_book(isbn)
        flash('Llibre tornat amb èxit!', 'success')
    elif borrower:
        flash('No pots tornar aquest llibre perquè no el tens prestat.', 'error')
    else:
        flash('Aquest llibre no està prestat.', 'error')
    return redirect(url_for('book_details', isbn=isbn))

@app.route('/covers/<filename>')
def serve_cover(filename):
    return send_from_directory('data/covers', filename)

@app.route('/politica-privacitat')
def politica_privacitat():
    if 'usuari' in session:
        return render_template('politica-privacitat.html', usuari=session['usuari'])
    return render_template('politica-privacitat.html')

@app.route('/contacte')
def contacte():
    if 'usuari' in session:
        return render_template('contacte.html', usuari=session['usuari'])
    return render_template('contacte.html')

if __name__ == '__main__':
    app.run(debug=True, port=5500)