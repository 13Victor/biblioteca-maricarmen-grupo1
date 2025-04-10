# 📚 Biblioteca MariCarmen Brito

![GitHub](https://img.shields.io/github/license/AWS2/biblioteca-maricarmen)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Django](https://img.shields.io/badge/Django-latest-green.svg)
![React](https://img.shields.io/badge/React-latest-61DAFB.svg)

> Software para la gestión de bibliotecas. En memoria de Mari Carmen Brito del Instituto Esteve Terradas i Illa de Cornellà de Llobregat.

<p align="center">
  <img src="https://github.com/user-attachments/assets/08ffc9f0-28a2-4c2c-b59c-e832676762b0" alt="Esteve Terradas Logo" width="70%">
</p>

## 🌟 Características

- ✅ Gestión completa de catálogo de libros
- ✅ Panel de administración para personal de biblioteca
- ✅ API RESTful para integración con otros sistemas
- ✅ Interfaz de usuario moderna con React
- ✅ Funcionalidades de búsqueda avanzada

## 📋 Requisitos previos

- Python 3.8+
- Git
- MySQL o MariaDB
- Node.js y npm (para el frontend React)

## 🚀 Instalación

### Clonar el repositorio

```bash
git clone https://github.com/AWS2/biblioteca-maricarmen
cd biblioteca-maricarmen
```

### Configurar el entorno virtual

```bash
# Instalación de dependencias del sistema (Debian/Ubuntu)
sudo apt update
sudo apt install python3-venv git libmysqlclient-dev python3-dev python3-mysqldb gcc pkgconf

# Crear y activar entorno virtual
python3 -m venv env
source env/bin/activate

# Instalar dependencias de Python
pip install -r requirements.txt
```

### Configurar la base de datos

```bash
# Crear archivo de configuración
cp .env.example .env

# Editar .env con tu configuración de base de datos
# nano .env

# Aplicar migraciones
./manage.py migrate

# Crear superusuario
./manage.py createsuperuser

# Cargar datos de prueba (opcional)
./manage.py loaddata testdb.json
```

### Iniciar el servidor de desarrollo

```bash
./manage.py runserver
```

Accede al panel de administración en: http://localhost:8000/admin/

## 🎨 Frontend React

Por defecto, acceder a http://localhost:8000/ mostrará solo un mensaje de bienvenida. Para activar la interfaz completa de React:

```bash
# Inicializar y actualizar el submódulo de React
git submodule init
git submodule update

# Desplegar React en el proyecto Django
./deploy-react.sh

# Iniciar el servidor
./manage.py runserver
```

Ahora podrás acceder a la interfaz completa en: http://localhost:8000/

## 🔑 API REST

### Obtener token de autenticación

```http
GET /api/token/
```

**Parámetros de autenticación básica:**
- `user`: nombre de usuario
- `password`: contraseña

**Ejemplo con curl:**
```bash
curl "localhost:8000/api/token/" -i -X GET -u admin:admin123
```

### Listar libros

```http
GET /api/llibres/
```

**Cabeceras requeridas:**
- `Authorization: Token {tu-token-aquí}`

## 📝 Documentación

La documentación completa está disponible en la [wiki del proyecto](https://github.com/AWS2/biblioteca-maricarmen/wiki).

## 🧪 Tests

Para ejecutar los tests:

```bash
./manage.py test
```

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor, revisa las [guías de contribución](CONTRIBUTING.md) antes de enviar un pull request.

1. Fork del repositorio
2. Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de tus cambios (`git commit -m 'Añade nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 🙏 Agradecimientos

- Mari Carmen Brito, por su dedicación a la educación
- Todo el equipo del Institut Esteve Terradas i Illa
- Comunidades de Django y React por sus excelentes recursos
