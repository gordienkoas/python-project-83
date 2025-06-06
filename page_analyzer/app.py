import os
from flask import Flask, render_template, request, redirect, flash, url_for
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from page_analyzer.data_base import (save_url, get_existing_urls,
                                     get_db_connection)
from page_analyzer.parser import parse_url
from page_analyzer.url_validator import validate_url


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def create_url():
    url_input = request.form.get('url')
    error_message = validate_url(url_input)
    if error_message:
        flash(error_message, 'error')
        return render_template('index.html', url=url_input), 422
    base_input_domain = parse_url(url_input)
    existing_urls = get_existing_urls()
    if existing_urls:
        for existing_url in existing_urls:
            if base_input_domain == parse_url(existing_url[1]):
                flash('Страница уже существует', 'error')
                return redirect(url_for('url_detail', url_id=existing_url[0]))
    url_id = save_url(url_input)
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('url_detail', url_id=url_id))


@app.route('/urls', methods=['GET'])
def list_urls():
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
    cursor.execute('SELECT * FROM url_checks '
                   'WHERE url_id = %s ORDER BY created_at DESC',
                   (url_id,))
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
        description_content = description_tag['content'] \
            if description_tag else None
        cur.execute(
            '''
            INSERT INTO url_checks 
            (url_id, status_code, h1, title, description) 
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (url_id, response.status_code, h1_content,
             title_content, description_content)
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