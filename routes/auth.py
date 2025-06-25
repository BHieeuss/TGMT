from flask import Blueprint, render_template, request, redirect, url_for, flash, session

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập (đơn giản cho demo)"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Đăng nhập đơn giản (trong thực tế nên sử dụng database và hash password)
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Đăng xuất"""
    session.clear()
    flash('Đã đăng xuất!', 'info')
    return redirect(url_for('auth.login'))
