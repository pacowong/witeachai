from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)

from werkzeug.exceptions import abort

import random
import os
import hashlib
import tempfile
import pandas
from wit import Wit
from gtts import gTTS 

from flask_chatbot.auth import login_required
from flask_chatbot.db import get_db

bp = Blueprint('classroom', __name__)

@bp.route('/simple_index')
def simple_index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, message, p.created AS created, author_id, username, r.body AS response, r.voice_filename'
        ' FROM post p'
        ' JOIN user u ON p.author_id = u.id'
        ' JOIN response r ON p.response_id = r.id'
        ' ORDER BY created DESC'
    ).fetchall()
    proj_name = g.chatbot_proj['proj_name']
    proj_asset_url = 'projs' + '/' + proj_name
    video_folder = os.path.join(current_app.static_folder, 'projs', proj_name, 'responses_videos')
    has_videos = dict()
    for post in posts:
        print(post)
        print(str(post['voice_filename']))
        has_videos[str(post['voice_filename'])] = os.path.isfile(os.path.join(video_folder, str(post['voice_filename'])+'.mp4'))
    return render_template(
        'classroom/simple_index.html',
        proj_asset_dir=proj_asset_url,
        posts=posts,
        has_videos=has_videos)


@bp.route('/', methods=('GET', 'POST'))
@login_required
def index():
    if request.method == 'POST':
        message = request.form['message']
        chatbot_proj_id = 1
        _, response_message = wit_ai_understand(message)

        if update_classroom_db(message, response_message):
            return redirect(url_for('classroom.index'))
            
    db = get_db()
    posts = db.execute(
        'SELECT p.id, message, p.created AS created, author_id, username, r.body AS response, r.voice_filename'
        ' FROM post p'
        ' JOIN user u ON p.author_id = u.id'
        ' JOIN response r ON p.response_id = r.id'
        ' ORDER BY created DESC'
    ).fetchall()
    proj_name = g.chatbot_proj['proj_name']
    proj_asset_url = 'projs' + '/' + proj_name
    video_folder = os.path.join(current_app.static_folder, 'projs', proj_name, 'responses_videos')
    has_videos = dict()
    for post in posts:
        print(post)
        print(str(post['voice_filename']))
        has_videos[str(post['voice_filename'])] = os.path.isfile(os.path.join(video_folder, str(post['voice_filename'])+'.mp4'))
    return render_template(
        'classroom/index.html',
        proj_asset_dir=proj_asset_url,
        posts=posts,
        has_videos=has_videos)


@bp.route('/send', methods=('GET', 'POST'))
@login_required
def send():
    if request.method == 'POST':
        message = request.form['message']
        chatbot_proj_id = 1
        _, response_message = wit_ai_understand(message)

        if update_classroom_db(message, response_message):
            return redirect(url_for('classroom.index'))

    return render_template('classroom/send.html')


@bp.route('/send_audio', methods=('GET', 'POST'))
@login_required
def send_audio():
    if request.method == 'POST':
        audio_fp = tempfile.TemporaryFile()
        audio_fp.write(request.data)
        audio_fp.seek(0)

        message, response_message = wit_ai_understand(audio_fp, audio_blob=True)
        audio_fp.close()

        if update_classroom_db(message, response_message):
            return redirect(url_for('classroom.index'))

    return render_template('classroom/recorder.html')


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, message, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Message id {0} doesn't exist.".format(id))

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        message = request.form['message']
        error = None

        if not message:
            error = 'Message is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET message = ?'
                ' WHERE id = ?',
                (message, id)
            )
            db.commit()
            return redirect(url_for('classroom.index'))

    return render_template('classroom/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('classform.index'))


def wit_ai_understand(msg, audio_blob=False):
    client = Wit(g.chatbot_proj['token'])
    user_resp = None
    if audio_blob:
        msg.seek(0)
        user_resp = client.speech(msg, {'Content-Type': 'audio/wav'})
    else:
        user_resp = client.message(msg)
    if user_resp['intents'] == []:
        return user_resp['text'], "Sorry, I don't understand your question. I can only answer questions within the topic."
    
    resp_intent = user_resp['intents'][0]
    proj_name = g.chatbot_proj['proj_name']
    responses_fpath = os.path.join(current_app.instance_path, proj_name, 'responses', resp_intent['name'] + '.txt')

    if not os.path.isfile(responses_fpath):
        print(f"Cannot response to {resp_intent['name']} because {responses_fpath} is missing")
        return user_resp['text'], "Sorry, I don't understand your question. Please ask your teacher for help."
    
    resp_df = pandas.read_csv(responses_fpath, sep='\t', encoding='utf-8', quotechar='"')

    ent_keys = set(user_resp['entities'].keys())
    df_keys = set(resp_df.columns)

    #TODO: Emit a log if the ent_keys has key that df_keys does not have
    common_keys = df_keys.intersection(ent_keys)

    resp_df_sel = None
    for k in common_keys:
        v = user_resp['entities'][k][0]['value']
        if resp_df_sel is None:
            resp_df_sel = resp_df[k] == v
        else:
            resp_df_sel = resp_df_sel & (resp_df[k] == v)

    resp_df = resp_df[resp_df_sel] #Related to the intent
    resp_df_idx = random.randint(0, resp_df['wit_response'].count()-1)
    return user_resp['text'], resp_df['wit_response'].iloc[resp_df_idx]


def update_classroom_db(message, response_message):
    chatbot_proj_id = 1
    response_id = 1
    error = None

    if not message:
        error = 'The message is required.'

    if error is not None:
        flash(error)
        return False
    else:
        m = hashlib.sha224()
        m.update(response_message.strip().encode("utf-8"))
        response_message_filename = m.hexdigest() + '.mp3'

        speech = gTTS(text=response_message, lang='en', slow=False)
        proj_name = g.chatbot_proj['proj_name']
        mp3_fpath = os.path.join(current_app.static_folder, 'projs', proj_name, 'responses_voices', response_message_filename)
        if not os.path.isfile(mp3_fpath):
            speech.save(mp3_fpath)

        # If two people are inserting at the same time, 
        # as long as they are using different cursors, cursor.lastrowid 
        # will return the id for the last row that cursor inserted.
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO response (chatbot_proj_id, body, voice_filename)'
            ' VALUES (?, ?, ?)',
            (chatbot_proj_id, response_message, response_message_filename)
        )
        response_id = cursor.lastrowid
        cursor.execute(
            'INSERT INTO post (chatbot_proj_id, message, author_id, response_id)'
            ' VALUES (?, ?, ?, ?)',
            (chatbot_proj_id, message, g.user['id'], response_id)
        )
        db.commit()
    return True