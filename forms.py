def validate_registration_form(data):
    errors = {}
    
    if not data.get('username') or len(data['username']) < 3:
        errors['username'] = 'Username must be at least 3 characters long'
    
    if not data.get('email') or '@' not in data['email']:
        errors['email'] = 'Valid email is required'
    
    if not data.get('password') or len(data['password']) < 6:
        errors['password'] = 'Password must be at least 6 characters long'
    
    if data.get('password') != data.get('confirm_password'):
        errors['confirm_password'] = 'Passwords do not match'
    
    return errors

def validate_login_form(data):
    errors = {}
    
    if not data.get('email'):
        errors['email'] = 'Email is required'
    
    if not data.get('password'):
        errors['password'] = 'Password is required'
    
    return errors

def validate_blog_post(data):
    errors = {}
    
    if not data.get('title') or len(data['title']) < 5:
        errors['title'] = 'Title must be at least 5 characters long'
    
    if not data.get('content') or len(data['content']) < 50:
        errors['content'] = 'Content must be at least 50 characters long'
    
    return errors

def validate_product_form(data):
    errors = {}
    
    if not data.get('name') or len(data['name']) < 3:
        errors['name'] = 'Product name is required'
    
    if not data.get('price') or float(data.get('price', 0)) <= 0:
        errors['price'] = 'Valid price is required'
    
    if not data.get('description') or len(data['description']) < 10:
        errors['description'] = 'Description must be at least 10 characters long'
    
    return errors