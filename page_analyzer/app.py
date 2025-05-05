import os
from flask import Flask, render_template, request, redirect, flash, url_for
import psycopg2
from dotenv import load_dotenv
import validators

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Замените на ваш секретный ключ


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        if not validators.url(url) or len(url) > 255:
            flash('Неверный URL-адрес!', 'error')
            return redirect(url_for('index'))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO urls (name) VALUES (%s)', (url,))
            conn.commit()
            flash('URL успешно добавлен!', 'success')
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Этот URL уже существует!', 'error')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('index'))

    return render_template('index.html')


@app.route('/urls', methods=['GET'])
def urls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls ORDER BY created_at DESC')
    urls = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:url_id>', methods=['GET'])
def url_detail(url_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = %s', (url_id,))
    url = cur.fetchone()
    cur.close()
    conn.close()

    if url is None:
        flash('URL не найден!', 'error')
        return redirect(url_for('urls'))

    return render_template('url_detail.html', url=url)


if __name__ == '__main__':
    app.run(debug=True)



#
# @app.route('/urls', methods=['POST'])
# def add_url():
#     pass
