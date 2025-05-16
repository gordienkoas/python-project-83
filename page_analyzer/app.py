import os
from flask import Flask, render_template, request, redirect, flash, url_for
import requests
import psycopg2
from dotenv import load_dotenv
import validators
from bs4 import BeautifulSoup
from urllib.parse import urlparse

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

app = Flask(__name__)
app.secret_key = 'SECRETFORMYPROJECT007'


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        return redirect(url_for('urls', url=url))
    return render_template('index.html')

@app.route('/urls', methods=['GET', 'POST'])
def urls():
    if request.method == 'POST':
        url = request.form.get('url')

        if not validators.url(url) or len(url) > 255:
            flash('Некорректный URL', 'error')
            return redirect(url_for('index')), 422  # Возвращаем ошибку 422 с переадресацией на главную страницу

        domain = urlparse(url).netloc

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute('SELECT id FROM urls WHERE name = %s', (domain,))
                    existing_url = cur.fetchone()

                    if existing_url:
                        url_id = existing_url[0]
                        flash('Страница уже существует', 'error')
                        return redirect(url_for('url_detail', url_id=url_id))

                    cur.execute('INSERT INTO urls (name) VALUES (%s) RETURNING id', (domain,))
                    url_id = cur.fetchone()[0]
                    conn.commit()
                    flash('Страница успешно добавлена', 'success')

                    return redirect(url_for('url_detail', url_id=url_id))
                except Exception as e:
                    conn.rollback()
                    flash(f'Произошла ошибка: {str(e)}', 'error')
                    return redirect(url_for('index')), 500  # Возвращаем ошибку 500 с переадресацией на главную страницу

    else:
        # Обработка GET-запроса
        url = request.args.get('url')
        if url:
            return redirect(url_for('urls'))  # Если URL передан, просто перенаправляем на тот же маршрут

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT u.id, u.name, u.created_at,
                           uc.status_code, uc.created_at AS last_check,
                           uc.h1, uc.title, uc.description
                    FROM urls u
                    LEFT JOIN url_checks uc ON u.id = uc.url_id
                    AND uc.created_at = (
                        SELECT MAX(created_at)
                        FROM url_checks 
                        WHERE url_id = u.id
                    )
                ''')
                urls = cur.fetchall()
                return render_template('urls.html', urls=urls)




@app.route('/urls/<int:url_id>', methods=['GET'])
def url_detail(url_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM urls WHERE id = %s', (url_id,))
    url_record = cursor.fetchone()
    cursor.execute('SELECT * FROM url_checks WHERE url_id = %s ORDER BY created_at DESC', (url_id,))
    checks = cursor.fetchall()
    cursor.close()
    conn.close()

    if url_record is None:
        flash('Сайт не найден.', 'error')
        return redirect(url_for('urls'))

    return render_template('result.html', url=url_record, checks=checks)


@app.route('/check_url/<int:url_id>', methods=['POST'])
def add_check(url_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT name FROM urls WHERE id = %s', (url_id,))
    url_row = cur.fetchone()

    if url_row is None:
        flash('URL не найден.', 'error')
        return redirect(url_for('urls'))

    url_name = url_row[0]

    # Проверка и добавление схемы к URL, если она отсутствует
    parsed_url = urlparse(url_name)
    if not parsed_url.scheme:
        url_name = 'http://' + url_name  # Добавляем http по умолчанию

    try:
        response = requests.get(url_name)
        response.raise_for_status()  # Проверка на ошибки HTTP

        # Парсинг HTML с помощью BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Извлечение SEO-данных
        h1_tag = soup.find('h1')
        title_tag = soup.find('title')
        description_tag = soup.find('meta', attrs={'name': 'description'})

        h1_content = h1_tag.text if h1_tag else None
        title_content = title_tag.text if title_tag else None
        description_content = description_tag['content'] if description_tag else None

        # Записываем код статуса и SEO-данные в базу данных
        cur.execute(
            '''
            INSERT INTO url_checks (url_id, status_code, h1, title, description) 
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (url_id, response.status_code, h1_content, title_content, description_content)
        )

        conn.commit()
        flash('Страница успешно проверена', 'success')
    except Exception:
        conn.rollback()
        flash('Произошла ошибка при проверке', 'error')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('url_detail', url_id=url_id))


if __name__ == '__main__':
    app.run(debug=True)