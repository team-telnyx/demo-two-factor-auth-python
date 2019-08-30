# Two factor authentication with Telnyx

## Configuration


Create a `config.cfg` file in your project directory. Flask will load this at startup. First, head into the Telnyx portal, provision an SMS number and messaging profile `<link>`, and create an API key `<link>`. Then add those to the config file.

    API_KEY='YOUR_API_KEY'
    FROM_NUMBER='YOUR_TELNYX_NUMBER'
**NOTE: This file contains a secret key, it should not be committed to source control.**

We’ll also place Flask in debug mode, assume all numbers are in the U.S., and specify the number of characters we'd like the OTP token to be.

    DEBUG=True
    COUNTRY_CODE='+1'
    TOKEN_LENGTH=4

## Token storage

We'll use a class to store tokens in memory for the purposes of this example. In a production environment, a traditional database would be appropriate. Create a class called `TokenStorage` with three methods. This class will store uppercase tokens as keys, with details about those tokens as values, and expose check and delete methods.

```python
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
```

## Server initialization

Setup a simple Flask app, load the config file, and configure the telnyx library. We'll also serve an `index.html` page, the full source of this is available on GitHub, but it includes a form that collects a phone number for validation.

```python
app = Flask(__name__)
app.config.from_pyfile('config.cfg')

telnyx.api_key = app.config['API_KEY']

@app.route('/')
def serve_index():
    return render_template('index.html')
```

## Token generation

We'll start with a simple method, `get_random_token_hex`, that generates a random string of hex characters to be used as OTP tokens.

```python
def get_random_token_hex(num_chars):
    byte_data = secrets.token_hex(math.ceil(num_chars / 2.0))
    return byte_data.upper()[:num_chars]
```

The `token_hex` method accepts a number of bytes, so we need to divide by two and and round up in order to ensure we get enough characters (two characters per byte), and then finally trim by the actual desired length. This allows us to support odd numbered token lengths.

Next, handle the form on the `/request` route. First this method normalizes the phone number.

```python
@app.route('/request', methods=['POST'])
def handle_request():
    phone_number = (request.form['phone']
                    .replace('-', '').replace('.', '')
                    .replace('(', '').replace(')', '')
                    .replace(' ', ''))
```

Then generate a token and add the token/phone number pair to the data store.

```python
    generated_token = get_random_token_hex(app.config['TOKEN_LENGTH'])
    TokenStorage.add_token(generated_token, phone_number)
```

Finally, send an SMS to the device and serve the verification page.

```python
    telnyx.Message.create(
        to=app.config['COUNTRY_CODE'] + phone_number,
        from_=app.config['FROM_NUMBER'],
        text='Your token is ' + generated_token
    )

    return render_template('verify.html')
```

## Token verification

The `verify.html` file includes a form that collects the token and sends it back to the server. If the token is valid, we'll clear it from the datastore and serve the success page.

```python
@app.route('/verify', methods=['POST'])
def handle_verify():
    token = request.form['token']

    if TokenStorage.token_is_valid(token):
        TokenStorage.clear_token(token)
        return render_template('verify_success.html')
```

Otherwise, send the user back to the verify form with an error message

```python
    else:
        return render_template('verify.html', display_error=True)
```

## Finishing up

At the end of the file, run the server.

```python
if __name__ == "__main__":
    app.run()
```

To start the application, run `python otp_demo.py` from within the virtualenv.
