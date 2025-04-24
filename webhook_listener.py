from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Verifica que el webhook es de tu repositorio y que es la rama 'dev'
    payload = request.json
    if payload and 'ref' in payload and payload['ref'] == 'refs/heads/dev':  # Cambia 'main' por 'dev'
        try:
            # Cambiar a la carpeta del proyecto y ejecutar los comandos
            subprocess.run(["cd", "/var/www/biblioteca-maricarmen-grupo1"], check=True)
            subprocess.run(["sudo", "chown", "-R", "super:super", "/var/www/biblioteca-maricarmen-grupo1"], check=True)
            subprocess.run(["./deploy-react.sh"], check=True)
            subprocess.run(["./manage.py", "collectstatic"], check=True)
            subprocess.run(["sudo", "chown", "-R", "www-data:www-data", "/var/www/biblioteca-maricarmen-grupo1"], check=True)
            subprocess.run(["sudo", "systemctl", "restart", "apache2"], check=True)

            return 'Deploy completo', 200
        except subprocess.CalledProcessError as e:
            return f'Error al ejecutar comandos: {str(e)}', 500
    else:
        return 'Webhook no válido', 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
