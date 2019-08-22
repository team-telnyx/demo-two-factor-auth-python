from flask import Flask, render_template, request
import secrets, telnyx, math
from datetime import datetime

class TokenStorage():
    tokens = {}

    @classmethod
    def add_token(cls, token, phone_number):
        cls.tokens[token] = {
            'phone_number': phone_number,
            'last_updated': datetime.now(),
            'token': token.upper()
        }
    
    @classmethod
    def token_is_valid(cls, token):
        return token.upper() in cls.tokens
    
    @classmethod
    def clear_token(cls, token):
        del TokenStorage.tokens[token.upper()]

app = Flask(__name__)
app.config.from_pyfile('config.cfg')

telnyx.api_key = app.config['API_KEY']

def get_random_token_hex(num_chars):
    byte_data = secrets.token_hex(math.ceil(num_chars / 2.0))
    return byte_data.upper()[:num_chars]

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/request', methods=['POST'])
def handle_request():
    phone_number = (request.form['phone']
                    .replace('-', '').replace('.', '')
                    .replace('(', '').replace(')', '')
                    .replace(' ', ''))
    generated_token = get_random_token_hex(app.config['TOKEN_LENGTH'])

    TokenStorage.add_token(generated_token, phone_number)

    telnyx.Message.create(
        to=app.config['COUNTRY_CODE'] + phone_number,
        from_=app.config['FROM_NUMBER'],
        text='Your token is ' + generated_token
    )
    
    return render_template('verify.html')

@app.route('/verify', methods=['POST'])
def handle_verify():
    token = request.form['token']

    if TokenStorage.token_is_valid(token):
        TokenStorage.clear_token(token)
        return render_template('verify_success.html')
    else:
        return render_template('verify.html', display_error=True)

if __name__ == "__main__":
    app.run()