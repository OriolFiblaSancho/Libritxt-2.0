# Classe per als llibres
class Book:
    def __init__(self, title, author, categories, isbn, language, release_year, cover):
        self._title = title
        self._author = author
        self._categories = categories
        self._isbn = isbn
        self._language = language
        self._release_year = release_year
        self._cover = cover

    # Getters
    @property
    def title(self):
        return self._title
    
    @property
    def author(self):
        return self._author

    @property
    def category(self):
        return self._category

    @property
    def isbn(self):
        return self._isbn
    
    @property
    def language(self):
        return self._language

    @property
    def release_year(self):
        return self._release_year

    @property
    def cover(self):
        return self._cover

# Classe pare dels usuaris    
class User:
    def __init__(self, id, name, password, role):
        self._id = id
        self._name = name
        self._password = password
        self._role = role

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def password(self):
        return self._password

    @property
    def role(self):
        return self._role
    
    def check_password(self, password_form):
        if password_form == self._password: return True
        else: return False

class Admin(User):
    def __init__(self, id, name, password_hash):
        super().__init__(id, name, password_hash, "admin")

class Reader(User):
    def __init__(self, id, name, password_hash):
        super().__init__(id, name, password_hash, "reader")

######################
# START REVIEW CLASSES
######################
class Review:
    def __init__(self, isbn, user_id, timestamp):
        self._isbn = isbn
        self._user_id = user_id
        self._timestamp = timestamp

    # Define type as the class name itself to leter be used on Flask
    @property
    def type(self):
        return self.__clas__.__name__

    @property
    def isbn(self):
        return self._isbn

    @property
    def user_id(self):
        return self._user_id

    @property
    def timestamp(self):
        return self._timestamp
    
    def display(self):
        raise NotImplementedError("Subclasses must implement display() for polymorphism")

class NumberReview(Review):
    def __init__(self, isbn, user_id, timestamp, rating):
        super().__init__(isbn, user_id, timestamp)
        self._rating = rating

    @property
    def rating(self):
        return self._rating
    
    def display(self):
        return f"Rating: {self._rating}/5"

class CommentReview(Review):
    def __init__(self, isbn, user_id, timestamp, comment):
        super().__init__(isbn, user_id, timestamp)
        self._comment = comment

    @property
    def comment(self):
        return self._comment
    
    def display(self):
        return f"Comment: {self._comment}"

class RecommendationReview(Review):
    def __init__(self, isbn, user_id, timestamp, recommendation):
        super().__init__(isbn, user_id, timestamp)
        self._recommendation = recommendation

    @property
    def recommendation(self):
        return self._recommendation
    
    def display(self):
        return f"Recommended {self._recommendation}"


# LOAN CLASS

class Loan:
    def __init__(self, isbn, user_id, loan_date, due_date, return_date=None):
        self._book_isbn = isbn
        self._user_id = user_id
        self._loan_date = loan_date
        self._due_date = due_date
        self._return_date = return_date

    @property
    def isbn(self):
        return self._isbn

    @property
    def user_id(self):
        return self._user_id

    @property
    def loan_date(self):
        return self._loan_date

    @property
    def due_date(self):
        return self._due_date

    @property
    def return_date(self):
        return self._return_date

    @return_date.setter
    def return_date(self, value):
        self._return_date = value
    
