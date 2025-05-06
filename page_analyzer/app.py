import os
from flask import Flask, render_template, request, redirect, flash, url_for
import requests
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

    # Объединяем запросы для получения всех URL и последней проверки
    cur.execute('''
        SELECT u.id, u.name, u.created_at, 
               uc.status_code, uc.created_at AS last_check
        FROM urls u
        LEFT JOIN url_checks uc ON u.id = uc.url_id
        AND uc.created_at = (
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
    cur = conn.cursor()

    # Получаем URL из базы данных
    cur.execute('SELECT name FROM urls WHERE id = %s', (url_id,))
    url = cur.fetchone()

    if url is None:
        flash('URL не найден.')
        return redirect(url_for('urls'))

    url_name = url[0]

    try:
        response = requests.get(url_name)
        response.raise_for_status()  # Проверка на ошибки HTTP
        status_code = response.status_code

        # Записываем код статуса в базу данных
        cur.execute('INSERT INTO url_checks (url_id, status_code) VALUES (%s, %s)', (url_id, status_code))
        conn.commit()

        flash(f'Проверка успешна! Код ответа: {status_code}')
    except requests.exceptions.RequestException as e:
        flash('Произошла ошибка при проверке.')
        # Логируем ошибку, если нужно
        print(f'Ошибка: {e}')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('urls'))



if __name__ == '__main__':
    app.run(debug=True)

