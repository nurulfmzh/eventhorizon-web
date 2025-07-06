from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc

app = Flask(__name__)
app.secret_key = '1234@dmin'  # Change this to a strong secret

# Azure SQL connection
server = 'eventhorizon-ca22034.database.windows.net'
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
    cursor.execute("SELECT id, name, date, description, location, capacity FROM Events")
    events = cursor.fetchall()
    return render_template('home.html', events=events)

@app.route('/dashboard')
def dashboard():
    if not session.get('organizer'):
        return redirect(url_for('login'))
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, description, location, capacity FROM Events")
    events = cursor.fetchall()
    return render_template('dashboard.html', events=events)

from flask import Flask, render_template, request, redirect, url_for, session, flash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Organizers WHERE username=? AND password=?", (username, password))
        organizer = cursor.fetchone()

        if organizer:
            session['organizer'] = organizer[0]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')  # Flash error message
            return redirect(url_for('login'))  # Redirect to login page

    return render_template('login.html')

@app.route('/create_event', methods=['POST'])
def create_event():
    if not session.get('organizer'):
        return redirect(url_for('login'))
    name = request.form['name']
    date = request.form['date']
    desc = request.form['description']
    location = request.form['location']
    capacity = request.form['capacity']
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Events (name, date, description, location, capacity) VALUES (?, ?, ?, ?, ?)",
        (name, date, desc, location, capacity)
    )
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
        location = request.form['location']
        capacity = request.form['capacity']
        cursor.execute(
            "UPDATE Events SET name=?, date=?, description=?, location=?, capacity=? WHERE id=?",
            (name, date, desc, location, capacity, event_id)
        )
        conn.commit()
        return redirect(url_for('dashboard'))
    else:
        cursor.execute("SELECT name, date, description, location, capacity FROM Events WHERE id=?", (event_id,))
        event = cursor.fetchone()
        return render_template('edit_event.html', event=event, event_id=event_id)

@app.route('/attendee/register', methods=['GET', 'POST'])
def attendee_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Attendees (name, email, password) VALUES (?, ?, ?)",
                           (name, email, password))
            conn.commit()
            flash('Account created successfully. Please log in.', 'success')
            return redirect(url_for('attendee_login'))
        except:
            flash('Email already registered.', 'warning')
            return redirect(url_for('attendee_register'))
    return render_template('attendee_register.html')

@app.route('/attendee/home')
def attendee_home():
    if not session.get('attendee_id'):
        return redirect(url_for('attendee_login'))

    attendee_id = session['attendee_id']
    cursor = conn.cursor()
    cursor.execute("""
        SELECT E.id, E.name, E.date, E.description, E.location, E.capacity
        FROM Events E
        JOIN Registrations R ON E.id = R.event_id
        WHERE R.attendee_id = ?
        ORDER BY E.date
    """, (attendee_id,))
    events = cursor.fetchall()
    return render_template('attendee_home.html', events=events)

@app.route('/attendee/register_event/<int:event_id>')
def attendee_register_event(event_id):
    if not session.get('attendee_id'):
        # Save intended event in session and redirect to login
        session['next_event'] = event_id
        return redirect(url_for('attendee_login'))

    attendee_id = session['attendee_id']
    cursor = conn.cursor()

    # Check if already registered
    cursor.execute("SELECT id FROM Registrations WHERE attendee_id=? AND event_id=?", (attendee_id, event_id))
    if cursor.fetchone():
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('attendee_my_events'))

    # Register the attendee
    cursor.execute("INSERT INTO Registrations (attendee_id, event_id) VALUES (?, ?)", (attendee_id, event_id))
    conn.commit()

    flash('Successfully registered for the event!', 'success')
    return redirect(url_for('attendee_my_events'))

@app.route('/attendee/login', methods=['GET', 'POST'])
def attendee_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Attendees WHERE email=? AND password=?", (email, password))
        attendee = cursor.fetchone()

        if attendee:
            session['attendee_id'] = attendee[0]

            # Check if they were trying to register for an event
            if 'next_event' in session:
                event_id = session.pop('next_event')
                return redirect(url_for('attendee_register_event', event_id=event_id))

            return redirect(url_for('attendee_home'))
        else:
            return 'Invalid credentials.'
    return render_template('attendee_login.html')

@app.route('/attendee/my_events')
def attendee_my_events():
    if not session.get('attendee_id'):
        return redirect(url_for('attendee_login'))

    attendee_id = session['attendee_id']
    cursor = conn.cursor()
    cursor.execute("""
        SELECT E.name, E.date, E.description, E.location
        FROM Events E
        JOIN Registrations R ON E.id = R.event_id
        WHERE R.attendee_id = ?
        ORDER BY E.date
    """, (attendee_id,))
    registered_events = cursor.fetchall()

    return render_template('attendee_my_events.html', events=registered_events)

@app.route('/logout')
def logout():
    session.clear()  # Clears both organizer and attendee session
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)