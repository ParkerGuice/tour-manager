from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, Tour, Show
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tours.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin = User(username='admin', password=hashed, role='admin')
        db.session.add(admin)
        db.session.commit()

with app.app_context():
    db.create_all()
    create_admin()

# Landing page
@app.route('/')
def home():
    return render_template('home.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed, role='viewer')
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    tours = Tour.query.all()
    return render_template('dashboard.html', tours=tours)

# Add tour - admin only
@app.route('/add_tour', methods=['GET', 'POST'])
@login_required
def add_tour():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        new_tour = Tour(
            artist_name=request.form['artist_name'],
            description=request.form['description']
        )
        db.session.add(new_tour)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_tour.html')

# Tour detail
@app.route('/tour/<int:id>')
@login_required
def tour_detail(id):
    tour = Tour.query.get_or_404(id)
    tour.shows.sort(key=lambda s: s.date)
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    return render_template('tour_detail.html', tour=tour, api_key=api_key)

# Add show - admin only
@app.route('/tour/<int:tour_id>/add_show', methods=['GET', 'POST'])
@login_required
def add_show(tour_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    tour = Tour.query.get_or_404(tour_id)
    if request.method == 'POST':
        new_show = Show(
            tour_id=tour_id,
            venue=request.form['venue'],
            city=request.form['city'],
            country=request.form['country'],
            date=request.form['date'],
            time=request.form['time'],
            capacity=request.form['capacity'],
            notes=request.form['notes']
        )
        db.session.add(new_show)
        db.session.commit()
        return redirect(url_for('tour_detail', id=tour_id))
    return render_template('add_show.html', tour=tour)

# Delete show - admin only
@app.route('/show/delete/<int:id>')
@login_required
def delete_show(id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    show = Show.query.get_or_404(id)
    tour_id = show.tour_id
    db.session.delete(show)
    db.session.commit()
    return redirect(url_for('tour_detail', id=tour_id))

# Delete tour - admin only
@app.route('/tour/delete/<int:id>')
@login_required
def delete_tour(id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    tour = Tour.query.get_or_404(id)
    db.session.delete(tour)
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)