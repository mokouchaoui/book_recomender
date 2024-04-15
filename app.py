from flask import Flask, render_template, url_for, request, redirect, session
import pandas as pd
from flask_mysqldb import MySQL
from flask_argon2 import Argon2
import subprocess

# Run the build script for TAILWIND CSS
subprocess.run(["npm", "run", "build:css"], check=True)

# Fetching data to be displayed
df = pd.read_csv('processed-dataset/pop.csv')
fdf = pd.read_csv('processed-dataset/final.csv')
sdf = pd.read_csv('processed-dataset/sugg.csv')

# Utility function for data
def data_util(book):
    book_data = []
    if sdf[sdf['book-title'] == book].index.shape[0] == 0:
        return book_data
    for name in sdf[sdf['book-title'] == book].values[0][1:]:
        for data in fdf[fdf['Book-Title'] == name].values:
            book_data.append(data)
    return book_data

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'recommender'
app.secret_key = 'your_secret_key'

mysql = MySQL(app)
argon2 = Argon2(app)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session and session['logged_in']:  # Check if user is already logged in
        return redirect(url_for('index'))  # Redirect to the home page if already logged in
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        # Ensure the SQL query is selecting the full_name and password (consider security and efficiency)
        cursor.execute("SELECT password, full_name FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and argon2.check_password_hash(user[0], password):  # Assuming user[0] is the hashed password
            session['logged_in'] = True
            session['username'] = username
            session['full_name'] = user[1]  # Assuming user[1] is the full name
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')




# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'logged_in' in session and session['logged_in']:  # Check ila mlogi
        return redirect(url_for('index'))  # raj3o l hhome page

    if request.method == 'POST':
            # Retrieve form data
            full_name = request.form['full_name']
            username = request.form['username']
            password = request.form['password']

            # hash data  f db
            hashed_password = argon2.generate_password_hash(password)

            cursor = mysql.connection.cursor()
            try:
                cursor.execute("INSERT INTO users (full_name, username, password) VALUES (%s, %s, %s)", (full_name, username, hashed_password))
                mysql.connection.commit()
                return redirect(url_for('login'))
            except Exception as e:
                mysql.connection.rollback()
                return f"An error occurred: {e}"
            finally:
                cursor.close()

    return render_template('register.html')


# Index route (ila mlogi)
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # Pass full_name from session to the template
    full_name = session.get('full_name', 'Guest')  # Default to 'Guest' if not found
    return render_template('index.html', full_name=full_name)


# Top 50 book recommendations
@app.route('/top50')
def top50():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template('top50.html',
                           book=list(df['Book-Title'].values[:50]),
                           author=list(df['Book-Author'].values[:50]),
                           img=list(df['Image-URL-M'].values[:50]),
                           votes=list(df['Total_Votes'].values[:50]),
                           rating=list(df['Average_Rating'].values[:50]),
                           p_25=df['Average_Rating'][:50].describe()['25%'],
                           p_50=df['Average_Rating'][:50].describe()['50%'],
                           p_75=df['Average_Rating'][:50].describe()['75%'])

# Top 5 recommendations
@app.route('/recommend')
def recommend_ui():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template('recommend.html', title="Recommended For You")

# Processing user input
@app.route("/recommend_books", methods=["POST"])
def recommend():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_input = request.form.get('user_input')
    suggestions = data_util(str(user_input).strip())

    if len(suggestions) == 0:
        return render_template('recommend.html', data=[], title="No suggestions found", book_title="")
    else:
        return render_template('recommend.html', data=suggestions[1:], title="Top 5 suggestions for ", book_title=str(user_input))

# About page
@app.route('/about')
def about():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('about.html')

if __name__ == "__main__":
    app.run(debug=True)
