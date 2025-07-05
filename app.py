from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc

app = Flask(__name__)
app.secret_key = '1234@dmin'  # Change this to a strong secret

# Azure SQL connection
server = 'sql-eventhorizon-server.database.windows.net'
database = 'db-eventhorizon'
username = 'sqladmin'
password = '@dmin1234'
driver= '{ODBC Driver 17 for SQL Server}'

conn = pyodbc.connect(
    'DRIVER=' + driver +
    ';SERVER=' + server +
    ';PORT=1433;DATABASE=' + database +
    ';UID=' + username +
    ';PWD=' + password
)

@app.route('/')
def home():
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, description FROM Events")
    events = cursor.fetchall()
    return render_template('home.html', events=events)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'password':
            session['organizer'] = True
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('organizer'):
        return redirect(url_for('login'))
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, description FROM Events")
    events = cursor.fetchall()
    return render_template('dashboard.html', events=events)

@app.route('/create_event', methods=['POST'])
def create_event():
    if not session.get('organizer'):
        return redirect(url_for('login'))
    name = request.form['name']
    date = request.form['date']
    desc = request.form['description']
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Events (name, date, description) VALUES (?, ?, ?)", (name, date, desc))
    conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if not session.get('organizer'):
        return redirect(url_for('login'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Events WHERE id=?", (event_id,))
    conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Attendees (event_id, name, email) VALUES (?, ?, ?)", (event_id, name, email))
        conn.commit()
        return 'You have successfully registered!'
    return render_template('register.html', event_id=event_id)

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if not session.get('organizer'):
        return redirect(url_for('login'))
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        date = request.form['date']
        desc = request.form['description']
        cursor.execute("UPDATE Events SET name=?, date=?, description=? WHERE id=?", (name, date, desc, event_id))
        conn.commit()
        return redirect(url_for('dashboard'))
    else:
        cursor.execute("SELECT name, date, description FROM Events WHERE id=?", (event_id,))
        event = cursor.fetchone()
        return render_template('edit_event.html', event=event, event_id=event_id)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
