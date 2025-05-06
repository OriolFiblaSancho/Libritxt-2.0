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
            # First get the lending details before deleting
            sql = """
                SELECT usuari_id, llibre_id, data_prestec, NOW() as data_retorn
                FROM prestecs 
                WHERE llibre_id = %s AND data_retorn IS NULL
            """
            cursor.execute(sql, (isbn,))
            prestec = cursor.fetchone()
            
            if not prestec:
                return False
                
            # Get the lending data
            usuari_id = prestec['usuari_id']
            llibre_id = prestec['llibre_id']
            data_prestec = prestec['data_prestec'].strftime("%Y-%m-%d")
            data_retorn = prestec['data_retorn'].strftime("%Y-%m-%d")
            
            # Delete the record from MySQL
            sql = "DELETE FROM prestecs WHERE llibre_id = %s AND data_retorn IS NULL"
            cursor.execute(sql, (isbn,))
            conn.commit()
            
            # Add to MongoDB historial_prestecs
            # First check if user exists in the historial collection
            historial_entry = historial_collection.find_one({"usuari_id": usuari_id})
            
            if historial_entry:
                # User exists, add to their historial array
                historial_collection.update_one(
                    {"usuari_id": usuari_id},
                    {"$push": {"historial": {
                        "llibre_id": llibre_id,
                        "data_prestec": data_prestec,
                        "data_retorn": data_retorn
                    }}}
                )
            else:
                # User doesn't exist, create new entry
                historial_collection.insert_one({
                    "usuari_id": usuari_id,
                    "historial": [
                        {
                            "llibre_id": llibre_id,
                            "data_prestec": data_prestec,
                            "data_retorn": data_retorn
                        }
                    ]
                })
            
            return True
    except pymysql.MySQLError as e:
        print(f"Error returning book: {e}")
        return False
    except Exception as e:
        print(f"Error updating loan history: {e}")
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

@app.route('/forYou', methods=['GET', 'POST'])
def for_you():
    if 'usuari' not in session:
        flash('Cal iniciar sessió per accedir a aquesta pàgina.', 'error')
        return redirect(url_for('login'))
    
    books = get_all_books()
    all_categories = get_all_categories(books)
    return render_template('forYou.html', usuari=session['usuari'], all_categories=all_categories)

@app.route('/logout')
def logout():
    session.pop('usuari', None)
    session.pop('role', None)
    flash('Has tancat sessió correctament.', 'success')
    return redirect(url_for('index'))

def get_book_by_isbn(isbn):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, titol, autor, categoria, any_publicacio FROM llibres WHERE id = %s"
            cursor.execute(sql, (isbn,))
            book_data = cursor.fetchone()
            
            if not book_data:
                return None
                
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
            description = text_collection.find_one({'llibre_id': int(book_isbn) - 1})
            description_text = description['text'] if description else None
            
            return {
                'isbn': book_isbn,
                'name': title,
                'author': author,
                'categories': categories,
                'editorial': None,  # Placeholder for editorial
                'release_year': publication_year,
                'cover': cover_url,
                'description': description_text
            }
    except pymysql.MySQLError as e:
        print(f"Error fetching book details: {e}")
        return None
    finally:
        conn.close()

def get_reviews_by_isbn(isbn):
    reviews = []
    try:
        # Query the MongoDB collection for reviews with matching llibre_id
        # Note: Convert isbn to integer since the llibre_id in MongoDB is stored as integer
        book_reviews = coments_collection.find_one({'llibre_id': int(isbn) - 1})
        
        if book_reviews:
            # Process numeric ratings
            if 'ressenyes' in book_reviews:
                for review in book_reviews['ressenyes']:
                    reviews.append({
                        'type': 'numeric' if review['tipus'] == 'numeric' else 'comment',
                        'user': review['usuari'],
                        'timestamp': review['data'],
                        'rating': review.get('estrelles') if review['tipus'] == 'numeric' else None,
                        'comment': review.get('text') if review['tipus'] == 'comment' else None
                    })
            
            # Process recommendations
            if 'recomanacions' in book_reviews:
                for recom in book_reviews['recomanacions']:
                    reviews.append({
                        'type': 'recommendation',
                        'user': recom['usuari'],
                        'timestamp': recom['data'],
                        'recommendation': recom['recomanat']
                    })
    except Exception as e:
        print(f"Error retrieving reviews from MongoDB: {e}")
    
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