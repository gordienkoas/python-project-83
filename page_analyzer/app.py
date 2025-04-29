import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/urls')
def all_urls():
    pass

@app.route('/urls', methods=['POST'])
def add_url():
    pass

__all__ = ['app']
if __name__ == '__main__':
    app.run()