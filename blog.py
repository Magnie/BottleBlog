# -*- coding: utf-8 -*-
__version__ = "1.0"
import hashlib
from time import strftime

from bottle import route, view, redirect, static_file, request

from pymongo import MongoClient
from pymongo import DESCENDING
client = MongoClient()
blog_db = client.bb

from sessions import Session
sessions = Session()

# Load Config
menu = blog_db.config.find({'option': 'menu'}, limit=1)
if menu:
    menu = menu[0]['menu']
installed = blog_db.config.find({'option': 'installed'}, limit=1)

def get_menu():
    "Return a menu with title and paths."
    global menu
    return menu

################
# Public Pages #
################
@route('/')
@view('template.html')
def home():
    "The home page/root directory of the site."
    # Check to see if the blog has been installed.
    if not installed:
        redirect('/install')

    # Get a list of posts to display. Max at 20. Ignore {'visible': False}.
    posts = []
    result = blog_db.posts.find({'visible': "on"})
    result = result.sort("id", direction=DESCENDING)
    for post in result[0:20]:
        posts.append(post)

    return {
        'title': "Joseph Augustine - Sterling Scholar",
        'menu': get_menu(),
        'content': "home.html",
        'kwargs': {
            'posts': posts,
            'admin': True if check_login() else False
        }
    }


@route('/view/<pid:int>')
@view('template.html')
def view_post(pid):
    "Display the requested blog post."
    # Get the post data and then return it with the page.
    post = blog_db.posts.find_one({'id': pid})
    print post
    if not post:
        redirect('/')

    return {
        'title': post['title'],
        'menu': get_menu(),
        'content': "view.html",
        'kwargs': {
            'post': post,
            'admin': True if check_login() else False
        }
    }


#################
# Private Pages #
#################
@route('/new')
@view('template.html')
def new():
    "Deliver a form for creating a new post."
    if not check_login():
        redirect('/')

    return {
        'title': 'New Blog Post',
        'menu': get_menu(),
        'content': "new.html"
    }

@route('/new', method="POST")
@view('template.html')
def new_post():
    "Add post to the database."
    if not check_login():
        redirect('/')

    sessions.start()

    # Gather data from the form and prepare the database entry.
    post = {}
    post['id'] = blog_db.config.find_one({'option': 'post_id'})['id']
    post['author'] = sessions.get('name')
    post['date'] = strftime("%x %I:%M:%S%p %Z")
    post['title'] = request.forms.get('title')
    post['html'] = request.forms.get('html')
    post['visible'] = request.forms.get('visible')

    # Insert into the database and increment the post ID in the config to keep
    # the IDs unique.
    blog_db.posts.insert(post)
    blog_db.config.update(
        {'option': 'post_id'},
        {'$inc': {'id': 1}}
    )
    redirect('/view/' + str(post['id']))

@route('/edit/<pid:int>')
@view('template.html')
def edit(pid):
    "Deliver a form for modifying a post."
    if not check_login():
        redirect('/')

    # Find the post, redirect to home if not found.
    post = blog_db.posts.find_one({'id': pid})
    if not post:
        redirect('/')

    return {
        'title': post['title'],
        'menu': get_menu(),
        'content': "edit.html",
        'kwargs': {'post': post}
    }

@route('/edit/<pid:int>', method="POST")
@view('template.html')
def edit_post(pid):
    "Make changing to the specified post."
    if not check_login():
        redirect('/')

    post = blog_db.posts.find_one({'id': pid})
    if not post:
        redirect('/')

    # Get updated data for the post.
    post = {}
    post['author'] = sessions.get('name')
    post['date'] = 'Editted: ' + strftime("%x %I:%M:%S%p %Z")
    post['title'] = request.forms.get('title')
    post['html'] = request.forms.get('html')
    post['visible'] = request.forms.get('visible')

    # Update the database entry.
    blog_db.posts.update(
        {'id': pid},
        {'$set': post}
    )

    redirect('/view/' + str(pid))

@route('/delete/<pid:int>')
@view('template.html')
def delete_post(pid):
    "Delete a post from the database."
    if not check_login():
        redirect('/')

    blog_db.posts.remove({'id': pid})

    redirect('/')

######################
# That Other Stuff.. #
######################
@route('/install')
@view('template.html')
def install():
    if installed:
        redirect('/')

    return {
        'title': 'Install BottleBlog',
        'menu': [{'title': 'Home', 'path': '/'}],
        'content': "install.html"
    }

@route('/install', method="POST")
@view('template.html')
def install_post():
    "The installation defaults."
    global installed, menu
    if installed:
        redirect('/')

    # Install the config.
    menu = [{'title': 'Home', 'path': '/'}]
    blog_db.config.insert({'option': 'menu', 'menu': menu})
    blog_db.config.insert({'option': 'post_id', 'id': 0})
    blog_db.config.insert({'option': 'installed', 'installed': True})
    menu = blog_db.config.find_one({'option': 'menu'})['menu']
    installed = True

    # Create the account.
    username = request.forms.get("username")
    password = request.forms.get("password")
    blog_db.users.insert({
        'username': username,
        'password': hash_sha256(password)
    })

    # Create installation/welcome post.
    post = {}
    post['id'] = blog_db.config.find_one({'option': 'post_id'})['id']
    post['author'] = 'BottleBlog Robot'
    post['date'] = strftime("%x %I:%M:%S%p %Z")
    post['title'] = 'Install Complete!'
    post['html'] = """
<p>
    The installation of BottleBlog is complete. You may now login to see the
    admin controls for maintaining your blog.
</p>
<p>
    Thank you for using BottleBlog!<br />
    -- Magnie Mozios
</p>
"""
    post['visible'] = "on"

    # Insert into the database and increment the post ID in the config to keep
    # the IDs unique.
    blog_db.posts.insert(post)
    blog_db.config.update(
        {'option': 'post_id'},
        {'$inc': {'id': 1}}
    )

    redirect('/')

@route('/login')
@view('template.html')
def login():
    "Deliver a form for logging in."
    return {
        'title': 'Login - Authorized Personel Only',
        'menu': get_menu(),
        'content': "login.html"
    }

@route('/login', method="POST")
@view('template.html')
def login_post():
    "Login the user."

    sessions.start()
    sessions.set('logged_in', False)

    if not sessions.get('attempts'):
        sessions.set('attempts', 0)

    attempts = sessions.get('attempts')
    if attempts > 3:
        redirect('http://google.com')

    username = request.forms.get("username")
    password = request.forms.get("password")

    # Check username and password to see if they match any DB entries.
    if blog_db.users.find_one({
                    'username': username,
                    'password': hash_sha256(password)
                    }):
        # Successful login.
        sessions.set('logged_in', True)
        sessions.set('name', username)
        print "Login as " + username + "."
        redirect('/')

    else:
        # Failed login.
        attempts += 1
        sessions.set('attempts', attempts)
        return {
            'title': 'Login - Authorized Personel Only',
            'menu': get_menu(),
            'content': "login.html"
        }

@route('/logout')
@view('template.html')
def logout():
    "Logout the user if they access this page."
    sessions.start()
    sessions.self_destruct()
    redirect('/')

@route('/static/<path:path>')
def serve_static(path):
    "Serve an unchanging file. Generally CSS, files, JS."
    return static_file(path, root='./static/')

def hash_sha256(text):
    "Quick hash function"
    return hashlib.sha256(str(text)+"n3verT-bEfort0ld?").hexdigest()

def check_login():
    "Check to see if the user is logged in."
    sessions.start()
    if sessions.get("logged_in"):
        return True

    return False