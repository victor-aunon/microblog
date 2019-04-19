from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from flask_login import current_user, login_required
from flask_babel import _, lazy_gettext as _l, get_locale
from flask_paginate import Pagination
from textblob import TextBlob
from app import db
from app.main import bp
from app.main.forms import EditProfileForm, PostForm, SearchForm, MessageForm
from app.models import User, Post, Message, Notification
from app.translate import translate

# g, current_app and current_user work like global variables, but are only accessible
# during the handling of a request, and only in the thread that is handling it.


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = TextBlob(form.post.data).detect_language()
        except:
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        # Send a notification to other users
        users = User.query.all()
        for user in users:
            if user.id != current_user.id:
                user.add_notification('new_post', {'state': 1,
                 'title': _("New post from %(username)s", username=current_user.username),
                 'icon':current_user.avatar(60), 'body': post.body,
                 'url': url_for('main.index')})
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'), category='success')
        # It is a standard practice to respond to a POST request generated by a web form
        # submission with a redirect. This helps mitigate an annoyance with how the refresh
        # command is implemented in web browsers
        return redirect(url_for('main.index'))

    current_user.add_notification('new_post', {'state': 0})
    current_user.add_notification('new_message', {'state': 0})
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POSTS_PER_PAGE']
    posts = current_user.followed_posts().paginate(page, per_page, False)
    if page == 1:
        first_this_page = 1
        last_this_page = len(posts.items)
    else:
        first_this_page = ((page - 1) * per_page) + 1
        last_this_page = first_this_page + len(posts.items) - 1
    pagination = Pagination(page=page, total=posts.total, search=False, per_page=per_page, bs_version=4,
                    display_msg=_('displaying %(first_this_page)d - %(last_this_page)d records of %(total)d', 
                                   first_this_page=first_this_page, last_this_page=last_this_page,
                                   total=posts.total))
    # next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
    # prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None
    # return render_template('index.html', title=_('Home Page'), form=form, posts=posts.items,
    #                         next_url=next_url, prev_url=prev_url)
    return render_template('index.html', title=_('Home Page'), form=form, pagination=pagination,
                            posts=posts.items)


# @bp.route('/posts', methods=['GET'])
# @login_required
# def posts():
#     page = request.args.get('page', 1, type=int)
#     posts = current_user.followed_posts().paginate(page, current_app.config['POSTS_PER_PAGE'], False)
#     return render_template('posts.html', posts=posts.items)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POSTS_PER_PAGE']
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, per_page, False)
    if page == 1:
        first_this_page = 1
        last_this_page = len(posts.items)
    else:
        first_this_page = ((page - 1) * per_page) + 1
        last_this_page = first_this_page + len(posts.items) - 1
    pagination = Pagination(page=page, total=posts.total, search=False, per_page=per_page, bs_version=4,
                    display_msg=_('displaying %(first_this_page)d - %(last_this_page)d records of %(total)d', 
                                   first_this_page=first_this_page, last_this_page=last_this_page,
                                   total=posts.total))
    # next_url = url_for('main.explore', page=posts.next_num) if posts.has_next else None
    # prev_url = url_for('main.explore', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title=_('Explore'), pagination=pagination, posts=posts.items)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POSTS_PER_PAGE']
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page, False)
    if page == 1:
        first_this_page = 1
        last_this_page = len(posts.items)
    else:
        first_this_page = ((page - 1) * per_page) + 1
        last_this_page = first_this_page + len(posts.items) - 1
    pagination = Pagination(page=page, total=posts.total, search=False, per_page=per_page, bs_version=4,
                    display_msg=_('displaying %(first_this_page)d - %(last_this_page)d records of %(total)d', 
                                   first_this_page=first_this_page, last_this_page=last_this_page,
                                   total=posts.total))
    return render_template('user.html',  title='{}'.format(username),
                            user=user, posts=posts.items, pagination=pagination)
    # next_url = url_for('main.user', username=user.username, page=posts.next_num) if posts.has_next else None
    # prev_url = url_for('main.user', username=user.username, page=posts.prev_num) if posts.has_prev else None
    # return render_template('user.html', user=user, posts=posts.items, next_url=next_url,
    #                         prev_url=prev_url)


@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
        # Get language code
    g.locale = str(get_locale())


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'), category='success')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'), form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username), category='warning')
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot follow yourself!'), category='warning')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are following %(username)s!', username=username), category='success')
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username), category='warning')
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot unfollow yourself!'))
        return redirect(url_for('main.user', username=username), category='warning')
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are not following %(username)s.', username=username), category='success')
    return redirect(url_for('main.user', username=username))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    response = translate(request.form['text'], request.form['source_language'],
                                       request.form['dest_language'])
    translation = response[0]['translations'][0]['text']
    return jsonify({'text': translation})


@bp.route('/search')
@login_required
def search():
    # validate() instead of validate_on_submit() because it is a GET method
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POSTS_PER_PAGE']
    posts, total = Post.search(g.search_form.q.data, page, per_page)
    if page == 1:
        first_this_page = 1
        last_this_page = len(posts)
    else:
        first_this_page = ((page - 1) * per_page) + 1
        last_this_page = first_this_page + len(posts) - 1
    pagination = Pagination(page=page, total=total, search=False, per_page=per_page, bs_version=4,
                    display_msg=_('displaying %(first_this_page)d - %(last_this_page)d records of %(total)d', 
                                   first_this_page=first_this_page, last_this_page=last_this_page,
                                   total=total))
    return render_template('search.html', title=_('Search'), posts=posts, pagination=pagination)
    # next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
    #     if total > page * current_app.config['POSTS_PER_PAGE'] else None
    # prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
    #     if page > 1 else None
    # return render_template('search.html', title=_('Search'), posts=posts, next_url=next_url,
    #                         prev_url=prev_url)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_popup.html', user=user)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        try:
            language = TextBlob(form.message.data).detect_language()
        except:
            language = ''
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data, language=language)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        user.add_notification('new_message', {'state': 1,
                 'title': _("New message from %(username)s", username=current_user.username),
                 'icon':current_user.avatar(60), 'body': msg.body,
                 'url': url_for('main.messages')})
        db.session.commit()
        flash(_('Your message has been sent.'), category='success')
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    current_user.add_notification('new_message', {'state': 0})
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POSTS_PER_PAGE']
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, per_page, False)
    if page == 1:
        first_this_page = 1
        last_this_page = len(messages.items)
    else:
        first_this_page = ((page - 1) * per_page) + 1
        last_this_page = first_this_page + len(messages.items) - 1
    pagination = Pagination(page=page, total=messages.total, search=False, per_page=per_page, bs_version=4,
                    display_msg=_('displaying %(first_this_page)d - %(last_this_page)d records of %(total)d', 
                                   first_this_page=first_this_page, last_this_page=last_this_page,
                                   total=messages.total))
    return render_template('messages.html', title=_('Messages'),
                             messages=messages.items, pagination=pagination)
    # next_url = url_for('main.messages', page=messages.next_num) \
    #     if messages.has_next else None
    # prev_url = url_for('main.messages', page=messages.prev_num) \
    #     if messages.has_prev else None
    # return render_template('messages.html', messages=messages.items,
    #                        next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name, 'data': n.get_data(), 'timestamp': n.timestamp
    } for n in notifications])
