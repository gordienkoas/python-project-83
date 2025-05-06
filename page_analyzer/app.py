import os
from flask import Flask, render_template, request, redirect, flash, url_for
import psycopg2
from dotenv import load_dotenv
import validators
from datetime import datetime

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

    # Получение всех URL и последней проверки для каждого URL
    cur.execute('''
        SELECT u.id, u.name, u.created_at, 
               uc.status_code, uc.created_at AS last_check
        FROM urls u
        LEFT JOIN url_checks uc ON u.id = uc.url_id
        WHERE uc.created_at = (
            SELECT MAX(created_at) 
            FROM url_checks 
            WHERE url_id = u.id
        )
        ORDER BY u.created_at DESC
    ''')
    urls = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:url_id>', methods=['GET'])
def url_detail(url_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM urls WHERE id = %s', (url_id,))
    url = cursor.fetchone()
    cursor.execute('SELECT * FROM url_checks WHERE url_id = %s', (url_id,))
    checks = cursor.fetchall()
    cursor.close()
    conn.close()
    if url is None:
        flash('Сайт не найден.', 'error')
        return redirect(url_for('urls'))
    return render_template('result.html', url=url, checks=checks)


@app.route('/urls/<int:url_id>/checks', methods=['POST'])
def add_check(url_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Здесь вы можете добавить логику для получения status_code, h1, title, description
        # На данный момент заполняем только url_id и created_at
        cursor.execute('INSERT INTO url_checks (url_id, created_at) VALUES (%s, %s)', (url_id, datetime.now()))
        conn.commit()
        flash('Проверка успешно добавлена!', 'success')
    except Exception as e:
        flash('Ошибка при добавлении проверки: ' + str(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('url_detail', url_id=url_id))


if __name__ == '__main__':
    app.run(debug=True)

