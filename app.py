import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agrifarma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Models with proper relationships
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profession = db.Column(db.String(100))
    expertise_level = db.Column(db.String(20))
    location = db.Column(db.String(200))
    profile_picture = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    is_consultant = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    threads = db.relationship('ForumThread', backref='author', lazy=True, foreign_keys='ForumThread.user_id')
    posts = db.relationship('ForumPost', backref='author', lazy=True, foreign_keys='ForumPost.user_id')
    blog_posts = db.relationship('BlogPost', backref='author', lazy=True)
    products = db.relationship('Product', backref='seller', lazy=True)
    consultant_profile = db.relationship('Consultant', backref='user', uselist=False)

class ForumCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_category.id'), nullable=True)
    
    # Relationship
    threads = db.relationship('ForumThread', backref='category', lazy=True)

class ForumThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('forum_category.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    posts = db.relationship('ForumPost', backref='thread', lazy=True, cascade='all, delete-orphan')

class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_thread.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    category = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(200))
    approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(200))
    stock_quantity = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Consultant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    specialization = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    hourly_rate = db.Column(db.Float)
    bio = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom filters
@app.template_filter('time_ago')
def time_ago_filter(value):
    if not value:
        return "Unknown"
    now = datetime.datetime.now()
    diff = now - value
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    elif diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "Just now"

@app.template_filter('is_new')
def is_new_filter(created_at, days=7):
    if not created_at:
        return False
    return (datetime.datetime.now() - created_at).days <= days

# Routes
@app.route('/')
def index():
    latest_posts = BlogPost.query.options(joinedload(BlogPost.author)).order_by(BlogPost.created_at.desc()).limit(3).all()
    latest_products = Product.query.options(joinedload(Product.seller)).order_by(Product.created_at.desc()).limit(4).all()
    return render_template('index.html', 
                         latest_posts=latest_posts, 
                         latest_products=latest_products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            profession=request.form.get('profession'),
            expertise_level=request.form.get('expertise_level'),
            location=request.form.get('location')
        )
        
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login failed. Check email and password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

# Forum Routes with eager loading
@app.route('/forum')
def forum():
    categories = ForumCategory.query.all()
    return render_template('forum/categories.html', categories=categories)

@app.route('/forum/category/<int:category_id>')
def forum_category(category_id):
    category = ForumCategory.query.get_or_404(category_id)
    # Use eager loading for author information
    threads = ForumThread.query.filter_by(category_id=category_id)\
                              .options(joinedload(ForumThread.author))\
                              .order_by(ForumThread.created_at.desc())\
                              .all()
    return render_template('forum/threads.html', category=category, threads=threads)

@app.route('/forum/thread/<int:thread_id>')
def forum_thread(thread_id):
    # Use eager loading for author information
    thread = ForumThread.query.options(joinedload(ForumThread.author))\
                             .get_or_404(thread_id)
    posts = ForumPost.query.filter_by(thread_id=thread_id)\
                          .options(joinedload(ForumPost.author))\
                          .order_by(ForumPost.created_at)\
                          .all()
    return render_template('forum/post.html', thread=thread, posts=posts)

@app.route('/forum/create_thread/<int:category_id>', methods=['POST'])
@login_required
def create_thread(category_id):
    title = request.form.get('title')
    content = request.form.get('content')
    
    # Add validation
    if not title or not title.strip():
        flash('Thread title is required!', 'danger')
        return redirect(url_for('forum_category', category_id=category_id))
    
    if not content or not content.strip():
        flash('Thread content is required!', 'danger')
        return redirect(url_for('forum_category', category_id=category_id))
    
    thread = ForumThread(
        title=title.strip(),
        category_id=category_id,
        user_id=current_user.id
    )
    db.session.add(thread)
    db.session.flush()
    
    post = ForumPost(
        content=content.strip(),
        thread_id=thread.id,
        user_id=current_user.id
    )
    db.session.add(post)
    db.session.commit()
    
    flash('Thread created successfully!', 'success')
    return redirect(url_for('forum_thread', thread_id=thread.id))

@app.route('/forum/thread/<int:thread_id>/reply', methods=['POST'])
@login_required
def post_reply(thread_id):
    thread = ForumThread.query.get_or_404(thread_id)
    content = request.form.get('content')
    
    if not content or not content.strip():
        flash('Reply content cannot be empty!', 'danger')
        return redirect(url_for('forum_thread', thread_id=thread_id))
    
    post = ForumPost(
        content=content.strip(),
        thread_id=thread_id,
        user_id=current_user.id
    )
    
    # Update thread's updated_at timestamp
    thread.updated_at = datetime.datetime.utcnow()
    
    db.session.add(post)
    db.session.commit()
    
    flash('Reply posted successfully!', 'success')
    return redirect(url_for('forum_thread', thread_id=thread_id))

# Blog Routes with proper error handling and eager loading
@app.route('/blog')
def blog():
    try:
        # Get category filter from request args
        category_filter = request.args.get('category')
        
        # Build query with eager loading
        query = BlogPost.query.options(joinedload(BlogPost.author))
        
        # Apply category filter if provided
        if category_filter:
            query = query.filter_by(category=category_filter)
        
        # Order by creation date and get all posts
        posts = query.order_by(BlogPost.created_at.desc()).all()
        
        # Always ensure posts is a list, even if empty
        if not posts:
            posts = []
            
        return render_template('blog/posts.html', posts=posts)
        
    except Exception as e:
        print(f"Error in blog route: {e}")
        # Return empty posts list in case of error
        return render_template('blog/posts.html', posts=[])

@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    try:
        # Use eager loading to load author information
        post = BlogPost.query.options(joinedload(BlogPost.author)).get_or_404(post_id)
        return render_template('blog/post_detail.html', post=post)
    except Exception as e:
        print(f"Error in blog_post route: {e}")
        flash('Blog post not found!', 'danger')
        return redirect(url_for('blog'))

@app.route('/blog/create', methods=['GET', 'POST'])
@login_required
def create_blog_post():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            content = request.form.get('content')
            category = request.form.get('category')
            
            # Validate required fields
            if not title or not content:
                flash('Title and content are required!', 'danger')
                return redirect(url_for('create_blog_post'))
            
            # Create excerpt from content
            excerpt = content[:150] + '...' if len(content) > 150 else content
            
            post = BlogPost(
                title=title,
                content=content,
                excerpt=excerpt,
                category=category,
                user_id=current_user.id
            )
            
            db.session.add(post)
            db.session.commit()
            flash('Blog post created successfully!', 'success')
            return redirect(url_for('blog'))
            
        except Exception as e:
            print(f"Error creating blog post: {e}")
            flash('Error creating blog post. Please try again.', 'danger')
            return redirect(url_for('create_blog_post'))
    
    return render_template('blog/create_post.html')

# Marketplace Routes with eager loading
@app.route('/marketplace')
def marketplace():
    # Use eager loading for seller information
    products = Product.query.options(joinedload(Product.seller)).all()
    return render_template('marketplace/products.html', products=products)

@app.route('/marketplace/product/<int:product_id>')
def product_detail(product_id):
    # Use eager loading for seller information
    product = Product.query.options(joinedload(Product.seller)).get_or_404(product_id)
    all_products = Product.query.options(joinedload(Product.seller)).all()
    return render_template('marketplace/product_detail.html', product=product, products=all_products)

@app.route('/marketplace/create', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        stock_quantity = int(request.form.get('stock_quantity', 1))
        
        product = Product(
            name=name,
            description=description,
            price=price,
            category=category,
            stock_quantity=stock_quantity,
            user_id=current_user.id
        )
        
        # Handle image upload
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename:
                filename = secure_filename(f"product_{current_user.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'products', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                product.image_url = f"/{file_path}"
        
        db.session.add(product)
        db.session.commit()
        flash('Product listed successfully!', 'success')
        return redirect(url_for('marketplace'))
    
    return render_template('marketplace/create_product.html')

# Product Management Routes
@app.route('/marketplace/my-products')
@login_required
def my_products():
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()
    return render_template('marketplace/my_products.html', products=products)

@app.route('/marketplace/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if user owns the product or is admin
    if product.user_id != current_user.id and not current_user.is_admin:
        flash('You can only edit your own products!', 'danger')
        return redirect(url_for('marketplace'))
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.category = request.form.get('category')
        product.stock_quantity = int(request.form.get('stock_quantity', 1))
        
        # Handle image upload
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename:
                # Delete old image if exists
                if product.image_url and os.path.exists(product.image_url.lstrip('/')):
                    try:
                        os.remove(product.image_url.lstrip('/'))
                    except:
                        pass
                
                filename = secure_filename(f"product_{current_user.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'products', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                product.image_url = f"/{file_path}"
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('product_detail', product_id=product.id))
    
    return render_template('marketplace/edit_product.html', product=product)

@app.route('/marketplace/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if user owns the product or is admin
    if product.user_id != current_user.id and not current_user.is_admin:
        flash('You can only delete your own products!', 'danger')
        return redirect(url_for('marketplace'))
    
    # Delete product image if exists
    if product.image_url and os.path.exists(product.image_url.lstrip('/')):
        try:
            os.remove(product.image_url.lstrip('/'))
        except:
            pass
    
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('marketplace'))

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied! Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    stats = {
        'total_users': User.query.count(),
        'total_products': Product.query.count(),
        'total_posts': BlogPost.query.count(),
        'total_threads': ForumThread.query.count(),
        'total_consultants': Consultant.query.count(),
        'pending_approvals': BlogPost.query.filter_by(approved=False).count() + 
                            Product.query.filter_by(approved=False).count() +
                            Consultant.query.filter_by(approved=False).count()
    }
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         users=User.query.all())

@app.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('Access denied! Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/toggle_user/<int:user_id>')
@login_required
def toggle_user_status(user_id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    # Here you would toggle user status (active/inactive)
    flash(f'User {user.username} status updated!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/approve_blog/<int:post_id>')
@login_required
def approve_blog_post(post_id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    post = BlogPost.query.get_or_404(post_id)
    post.approved = True
    db.session.commit()
    flash('Blog post approved!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_product/<int:product_id>')
@login_required
def approve_product(product_id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(product_id)
    product.approved = True
    db.session.commit()
    flash('Product approved!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_consultant/<int:consultant_id>')
@login_required
def approve_consultant(consultant_id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    consultant = Consultant.query.get_or_404(consultant_id)
    consultant.approved = True
    db.session.commit()
    flash('Consultant approved!', 'success')
    return redirect(url_for('admin_dashboard'))

# Profile Management Routes
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.username = request.form.get('username')
    current_user.email = request.form.get('email')
    current_user.profession = request.form.get('profession')
    current_user.expertise_level = request.form.get('expertise_level')
    current_user.location = request.form.get('location')
    
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename:
            filename = secure_filename(f"user_{current_user.id}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
            current_user.profile_picture = f"/{file_path}"
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect!', 'danger')
        return redirect(url_for('profile'))
    
    if new_password != confirm_new_password:
        flash('New passwords do not match!', 'danger')
        return redirect(url_for('profile'))
    
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

# Consultancy Routes with eager loading
@app.route('/consultants')
def consultants():
    # Use eager loading for user information
    consultants = Consultant.query.options(joinedload(Consultant.user)).all()
    return render_template('consultancy/consultants.html', consultants=consultants)

@app.route('/consultant/<int:consultant_id>')
def consultant_detail(consultant_id):
    # Use eager loading for user information
    consultant = Consultant.query.options(joinedload(Consultant.user)).get_or_404(consultant_id)
    all_consultants = Consultant.query.options(joinedload(Consultant.user)).all()
    return render_template('consultancy/consultant_detail.html', 
                         consultant=consultant, 
                         consultants=all_consultants)

@app.route('/become_consultant', methods=['GET', 'POST'])
@login_required
def become_consultant():
    if request.method == 'POST':
        specialization = request.form.get('specialization')
        experience = int(request.form.get('experience'))
        hourly_rate = float(request.form.get('hourly_rate'))
        bio = request.form.get('bio')
        
        consultant = Consultant(
            user_id=current_user.id,
            specialization=specialization,
            experience=experience,
            hourly_rate=hourly_rate,
            bio=bio
        )
        
        db.session.add(consultant)
        current_user.is_consultant = True
        db.session.commit()
        
        flash('Consultant application submitted successfully!', 'success')
        return redirect(url_for('consultants'))
    
    return render_template('consultancy/become_consultant.html')

# Initialize database with sample data
def init_db():
    # Create sample forum categories
    categories = [
        ForumCategory(name='Crops', description='Discussion about various crops'),
        ForumCategory(name='Livestock', description='Animal farming discussions'),
        ForumCategory(name='Irrigation', description='Water management topics'),
        ForumCategory(name='Soil Health', description='Soil management and fertility'),
        ForumCategory(name='Market Prices', description='Discuss current market rates')
    ]
    
    for category in categories:
        if not ForumCategory.query.filter_by(name=category.name).first():
            db.session.add(category)
    
    # Create admin user
    admin_user = User.query.filter_by(email='admin@agrifarma.com').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@agrifarma.com',
            password_hash=generate_password_hash('admin123'),
            profession='Administrator',
            expertise_level='expert',
            location='Sindh, Pakistan',
            is_admin=True
        )
        db.session.add(admin_user)
        print("✅ Admin user created: admin@agrifarma.com / admin123")
    
    # Create sample user
    sample_user = User.query.filter_by(email='farmer@agrifarma.com').first()
    if not sample_user:
        sample_user = User(
            username='farmerali',
            email='farmer@agrifarma.com',
            password_hash=generate_password_hash('farmer123'),
            profession='Farmer',
            expertise_level='intermediate',
            location='Sukkur, Sindh'
        )
        db.session.add(sample_user)
        print("✅ Sample user created: farmer@agrifarma.com / farmer123")
    
    # Commit users first to get their IDs
    db.session.commit()
    
    # Now create sample blog posts with the committed user IDs
    sample_blog_posts = [
        BlogPost(
            title="Organic Farming Success Story in Sindh",
            content="Discover how farmer Ali transformed his traditional farm into a successful organic operation...",
            excerpt="How one farmer in Sindh achieved remarkable success with organic farming techniques...",
            category="Success Stories",
            user_id=admin_user.id
        ),
        BlogPost(
            title="Modern Irrigation Techniques for Water Conservation",
            content="Learn about drip irrigation and other water-saving methods that can increase your yield...",
            excerpt="Effective water management strategies for modern farming...",
            category="Farming Techniques", 
            user_id=sample_user.id
        ),
        BlogPost(
            title="Understanding Soil Health for Better Crops",
            content="Comprehensive guide to soil testing, nutrient management, and maintaining soil fertility...",
            excerpt="Essential tips for maintaining healthy soil and maximizing crop production...",
            category="Soil Health",
            user_id=admin_user.id
        )
    ]
    
    for post in sample_blog_posts:
        if not BlogPost.query.filter_by(title=post.title).first():
            db.session.add(post)
    
    db.session.commit()
    print("✅ Sample blog posts created")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()
    print("🚀 AgriFarma is running! Access at: http://localhost:5000")
    print("👤 Admin Login: admin@agrifarma.com / admin123")
    print("👨‍🌾 Sample User: farmer@agrifarma.com / farmer123")
    app.run(debug=True)


