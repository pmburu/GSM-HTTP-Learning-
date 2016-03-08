from server import app
import os


HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 3000))
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'


app.run(
    host='0.0.0.0',
    port=3000,
    debug=True,
)
