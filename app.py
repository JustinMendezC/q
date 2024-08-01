from flask import Flask, jsonify, request, render_template, url_for
import subprocess
import threading
import os
from ansi2html import Ansi2HTMLConverter
import re

app = Flask(__name__)

conv = Ansi2HTMLConverter()

process = None
output_lines = []

ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

def read_process_output(pipe):
    global output_lines
    for line in iter(pipe.readline, ''):
        clean_line = ansi_escape.sub('', line).strip()
        output_lines.append(clean_line)
    pipe.close()


def start_process():
    global process, output_lines
    if process is not None and process.poll() is None:
        return

    output_lines = []
    process = subprocess.Popen(['python', 'server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    threading.Thread(target=read_process_output, args=(process.stdout,)).start()
    threading.Thread(target=read_process_output, args=(process.stderr,)).start()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/consola')
def consola():
    return render_template('consola.html')

@app.route('/archivos', defaults={'path': ''})
@app.route('/archivos/<path:path>')
def archivos(path):
    base_path = os.path.join('servidor_minecraft', path)
    if os.path.isdir(base_path):
        files = os.listdir(base_path)
        return render_template('archivos.html', files=files, path=path, os=os, base_path=base_path)
    else:
        return "No se encontró la carpeta."

@app.route('/editar_archivo/<path:path>', methods=['GET', 'POST'])
def editar_archivo(path):
    file_path = os.path.join('servidor_minecraft', path)
    if request.method == 'POST':
        contenido = request.form['contenido']
        with open(file_path, 'w') as f:
            f.write(contenido)
        return f'<script>alert("Archivo guardado correctamente."); window.location.href = "{url_for("archivos", path=os.path.dirname(path))}";</script>'
    with open(file_path, 'r') as f:
        contenido = f.read()
    return render_template('editar_archivo.html', path=path, contenido=contenido)

@app.route('/iniciar_server', methods=['POST'])
def iniciar_server():
    start_process()
    return jsonify(respuesta='server.py iniciado.')

@app.route('/enviar_opcion', methods=['POST'])
def enviar_opcion():
    opcion = request.json['opcion']
    if process and process.poll() is None:
        process.stdin.write(f'{opcion}\n')
        process.stdin.flush()
        return jsonify(respuesta=f'Opción {opcion} enviada.')
    return jsonify(respuesta='El proceso esta apagado')

@app.route('/enviar_comando', methods=['POST'])
def enviar_comando():
    comando = request.json['comando']
    if process and process.poll() is None:
        process.stdin.write(f'{comando}\n')
        process.stdin.flush()
        return jsonify(respuesta=f'Comando "{comando}" enviado.')
    return jsonify(respuesta='El proceso esta apagado')

@app.route('/obtener_salida', methods=['GET'])
def obtener_salida():
    global output_lines
    return jsonify(salida=output_lines)

@app.route('/apagar_servidor', methods=['POST'])
def apagar_servidor():
    if process and process.poll() is None:
        process.stdin.write('stop\n')
        process.stdin.flush()
        process.wait()  
        return jsonify(respuesta='Servidor apagado')
    return jsonify(respuesta='El proceso esta apagado')

if __name__ == '__main__':
    app.run(debug=True)
