import sqlite3
import json
import re
from datetime import datetime

# ~* Dictionary that contains int/str status -> str/int status
status_int_to_str = { 0: "Unread",
                      1: "Read",
                      2: "Reading",
                      3: "Going to read" }

# & Converts list/tuple/dict etc to JSON
def to_json(to_json_obj: list | tuple | dict) -> str:
    jsoned_obj = json.dumps(to_json_obj)
    return jsoned_obj


# & Converts json (string) to list
def from_json(jsoned_obj: str) -> list | tuple | dict:
    unjsoned_obj = json.loads(jsoned_obj)
    return unjsoned_obj


# & Converts string date "23.05.11" or "23/05/11" to datetime
def str_to_date(date_str: str) -> int:
    split_char = '.' if ('.' in date_str) else ('/' if ('/' in date_str) else ('-' if ('-' in date_str) else ''))
    if (not split_char): return

    date = (int(ymd) for ymd in date_str.split(split_char))
    date = datetime(*date)
    return date


# & Converts int date to str
def int_to_str(date_int: int) -> datetime:
    ymd = []
    for _ in range(3):
        str_ymd = str(date_int%100)
        ymd.append('0'+str_ymd if len(str_ymd)==1 else str_ymd)
        date_int //= 100
    ymd[2]=str(int(ymd[2])+2000)
    ymd.reverse()
    date = '-'.join(ymd)
    return date


# & Converts int date to datetime
def int_to_date(date_int: int) -> datetime:
    ymd = []
    for _ in range(3):
        ymd.append(date_int%100)
        date_int //= 100
    date = datetime(*ymd)
    return date


# & Datetime date to int
def date_to_int(date: datetime) -> int:
    return date.day+date.month*100+((date.year)-2000)*10000


# & Class to interact with database
class Database():
    def __init__(self, file: str):
        self.db = sqlite3.connect(file)
        self.cursor = self.db.cursor()
    
    # & Creates table in database
    # ? dates are stored like this 23.05.07 -> 230507
    # ? status is 0-unread, 1-read, 2-reading, 3-going to read
    # ? genres are stored as json-text
    def create_table(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS books (
                            id INTEGER PRIMARY KEY,
                            name VARCHAR,
                            author VARCHAR,
                            rating REAL,
                            ratings_json TEXT,
                            genres_json TEXT,
                            description TEXT,
                            starting_date UNSIGNED INTEGER,
                            ending_date UNSIGNED INTEGER,
                            status TINYINT
                            )""")

    # & Is book in database
    def is_book_in_db(self, name: str) -> bool:
        self.cursor.execute("""SELECT name FROM books WHERE name = ?""", (name,))
        return False if (self.cursor.fetchone() is None) else True

    # & Inserts a row into the table
    def insert(self, name: str, author: str, ratings: list[int], genres: list[str], description: str, starting_date: str, ending_date: str, status: int):
        starting_date = str_to_date(starting_date)
        starting_date = date_to_int(starting_date) if starting_date else 0
        ending_date = str_to_date(ending_date)
        ending_date = date_to_int(ending_date) if ending_date and starting_date else 0

        rating = round(sum(ratings)/len(ratings), 2) if ratings else -1

        genres = to_json(genres)
        ratings = to_json(ratings)

        if (self.is_book_in_db(name)):
            print("Book is already added")
            return

        self.cursor.execute("""INSERT INTO books VALUES (null, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                            (name, author, rating, ratings, genres, description, starting_date, ending_date, status))
        self.db.commit()

    # & Gets all info of a book by it's name
    def get_info(self, name: str) -> list:
        if (not self.is_book_in_db(name)):
            print("\nBook is not in the database")
            return []
        self.cursor.execute("""SELECT * FROM books WHERE name = ?""", (name,))
        return self.cursor.fetchone()

    # & Gets all ratings of book, so then it can get the average rating
    def get_ratings(self, name) -> list[int]:
        if (not self.is_book_in_db(name)):
            return []
        ratings = []
        try:
            ratings += from_json(self.get_info(name)[4])
        except TypeError:
            ...
        return ratings
    
    # & Updates rating of book to a new one after it gets new rating
    def update_rating(self, name: str, new_rating: int):
        if (not self.is_book_in_db(name)):
            print("This book is not in database")
            return
        ratings = self.get_ratings(name) + [new_rating]
        rating = round(sum(ratings)/len(ratings), 2)
        ratings = to_json(ratings)
        self.cursor.execute("""UPDATE books SET ratings_json = ? WHERE name = ?""", (ratings, name))
        self.cursor.execute("""UPDATE books SET rating = ? WHERE name = ?""", (rating, name))
        self.db.commit()

    # & Updates status of book
    def update_status(self, name: str, new_status: int):
        if (not self.is_book_in_db(name)):
            print("This book is not in database")
            return
        self.cursor.execute("""SELECT status FROM books WHERE name = ?""", (name,))
        if (new_status == 2):
            starting_date = input("\nInput the date when you started to read (YYYY/MM/DD): ")
            starting_date = str_to_date(starting_date)
            starting_date = date_to_int(starting_date)
            self.cursor.execute("""UPDATE books SET starting_date = ? WHERE name = ?""", (starting_date, name))
        elif (new_status == 1):
            ending_date = input("\nInput the date when you ended reading (YYYY/MM/DD): ")
            ending_date = str_to_date(ending_date)
            ending_date = date_to_int(ending_date)
            self.cursor.execute("""UPDATE books SET ending_date = ? WHERE name = ?""", (ending_date, name))
        self.cursor.execute("""UPDATE books SET status = ? WHERE name = ?""", (new_status, name))
        self.db.commit()

    # & Closes database and cursor
    def close(self):
        self.cursor.close()
        self.db.close()


# & User inputs information about book
def input_info():
    # ^ Input name
    name = input("Write the name of the book: ")
    yield name
    # ^ Input author
    author = input("\nWho is the author?: ")
    yield author
    # ^ Input description
    description = input("\nWrite a short description of the book: ")
    yield description
    # ^ Input genres
    genres = []
    genre = True
    print("\nInput genres, input nothing when you want to finish")
    i = 1
    while (genre):
        genre = input(f"{i} genre: ")
        genres.append(genre)
        i+=1
    genres = genres[:-1]
    yield genres
    # ^ Input rating
    while True:
        try:
            rating = int(input("\nRate this book: "))
            if (0 < rating > 10): 
                raise(ValueError)
            break
        except ValueError:
            ...   
    yield rating
    # ^ Input status
    while True:
        try:
            status = int(input("\nInput the status of the book. 1 - unread, 2 - read, 3 - reading, 4 - going to read: ")) - 1
            if (0 < status > 3): 
                raise(ValueError)
            break
        except ValueError:
            ...   
    yield status

    # ~ Checking what else need to input (starting date/ending date)
    if (status in (0, 3)):
        print("Thank you for your opinion!")
        return
    
    # ^ Input starting date
    regex = r"^\d{2}|\d{4}\.\d{2}\.\d{2}$"
    starting_date = ""
    if (status in (1, 2)):
        while (not re.match(regex, starting_date)):
            starting_date = input("\nInput the date when you started to read (YYYY/MM/DD): ")
    yield starting_date
    
    # ^ Input ending date
    ending_date = ""
    if (status == 1):
        while (not re.match(regex, ending_date)):
            ending_date = input("\nInput the date when you ended reading (YYYY/MM/DD): ")
    yield ending_date
            

def main():
    db = Database("database.db")
    db.create_table()
    while (True):
        func = input("Input function: ")
        print("\n")
        # ? Help function, writes info about other functions
        if (func == "/help"):
            print("/help - Information about other functions\n/end - Stops program\n/add - Add new book into the database\n/rate - Rate a book you want\n/status - Update status of the book\n\t1 - Unread\n\t2 - Read\n\t3 - Reading\n\t4 - Going to read\n/getinfo - Get all the information about a book")            

        # ? End function, ends program
        elif (func == "/end"):
            print("See you next time!")
            break

        # ? Add function, adds other book to database
        elif (func == "/add"):
            name, description, author, genres, rating, status, starting_date, ending_date = input_info()

            ratings = db.get_ratings(name) + [rating]
            db.insert(name, author, ratings, genres, description, starting_date, ending_date, status)

        # ? Rate function, rates a book
        elif (func == "/rate"):
            # ^ Input name
            name = input("Write the name of the book: ")
            
            # ^ Input rating
            while True:
                try:
                    rating = int(input("\nRate this book: "))
                    if (0 < rating > 10): 
                      raise(ValueError)
                    break
                except ValueError:
                    ...   
            db.update_rating(name, rating)
    
        # ? Status function, changes status of the book readment
        elif (func == "/status"):
            # ^ Input name
            name = input("Write the name of the book: ")
            
            # ^ Input rating
            while True:
                try:
                    status = int(input("\nWrite the new status. 1 - unread, 2 - read, 3 - reading, 4 - going to read: ")) - 1
                    if (0 < status > 3): 
                      raise(ValueError)
                    break
                except ValueError:
                    ...   
            db.update_status(name, status)    

        # ? Getinfo function, tells all the information about the book
        elif (func == "/getinfo"):
            # ^ Input name
            name = input("Write the name of the book: ")
            
            info = db.get_info(name)
            if (info):
                author, rating, _, genres, description, starting_date, ending_date, status = info[2:]
                genres = from_json(genres)
                starting_date = int_to_str(starting_date)
                ending_date = int_to_str(ending_date)
                print(f"\n{name} ({author})\n{", ".join(genres)}\n{description}\n{status_int_to_str[status]:}{(f"\nStarting date: {starting_date}\nEnding date: {ending_date}" if status==1 else f"\nStarting date: {starting_date}" if status==2 else "")}\n{rating}/10")

        # ? Not supported function
        else:
            print("Function is not supported")
        print("\n\n")

    db.close()


if __name__ == "__main__":
    main()
