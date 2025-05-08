from django.contrib.auth import authenticate
from ninja import NinjaAPI, Schema, Query
from ninja.security import HttpBasicAuth, HttpBearer
from django.db.models.functions import Substr, Length

from .models import *
from typing import List, Optional, Union, Literal
import secrets
from django.db.models import Q
import re  # Importar módulo para manejar signos de puntuación

api = NinjaAPI()


class SearchSuggestionOut(Schema):
    id: int
    titol: str
    autor: Optional[str]
    tipus: str

class ExemplarStateCount(Schema):
    disponible: int = 0
    exclos_prestec: int = 0
    baixa: int = 0

# Schema para los resultados de búsqueda
class SearchResultOut(Schema):
    id: int
    titol: str
    titol_original: Optional[str] = None
    autor: Optional[str] = None
    tipus: str
    # General fields from Cataleg
    CDU: Optional[str] = None
    signatura: Optional[str] = None
    data_edicio: Optional[str] = None  # Keep dates as strings in API
    resum: Optional[str] = None
    anotacions: Optional[str] = None
    mides: Optional[str] = None
    # Llibre specific fields
    editorial: Optional[str] = None
    ISBN: Optional[str] = None
    colleccio: Optional[str] = None
    lloc: Optional[str] = None
    pagines: Optional[int] = None
    # Revista specific fields
    ISSN: Optional[str] = None
    # CD/DVD/BR specific fields
    discografica: Optional[str] = None
    productora: Optional[str] = None
    duracio: Optional[str] = None
    # Dispositiu specific fields
    marca: Optional[str] = None
    model: Optional[str] = None
    # Estado del ejemplar
    exclos_prestec: Optional[bool] = None
    baixa: Optional[bool] = None
    # References to other models
    pais: Optional[dict] = None
    llengua: Optional[dict] = None
    tags: Optional[List[dict]] = None
    exemplar_counts: ExemplarStateCount = None

# Endpoint que devuelve ejemplares que coincidan con búsqueda
class ExemplarSearchOut(Schema):
    id: int
    registre: str
    titol: str
    autor: Optional[str]
    editorial: Optional[str]
    tipus: str
    exclos_prestec: bool
    baixa: bool

@api.get("/exemplars/search/", response=List[ExemplarSearchOut])
def search_exemplars(request, q: Optional[str] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), exact: Optional[str] = Query(None)):
    """
    Endpoint para buscar ejemplares por texto, rango de códigos o código específico.
    """
    exemplars = Exemplar.objects.select_related("cataleg").all()

    # Formatear start y end para que tengan 6 caracteres con ceros a la izquierda
    if start:
        start = start.zfill(6)
    if end:
        end = end.zfill(6)

    if q:
        # Buscar por título, autor o editorial
        exemplars = exemplars.filter(
            Q(cataleg__titol__icontains=q) |
            Q(cataleg__autor__icontains=q) |
            Q(cataleg__llibre__editorial__icontains=q)
        )
    elif start and end:
        # Buscar por rango de los últimos 6 dígitos de registre (inclusive)
        exemplars = exemplars.annotate(
            registre_suffix=Substr('registre', Length('registre') - 5, 6)  # Extraer los últimos 6 dígitos
        ).filter(
            registre_suffix__gte=start,
            registre_suffix__lte=end
        )
    elif start:
        # Buscar por código específico (últimos 6 dígitos)
        exemplars = exemplars.annotate(
            registre_suffix=Substr('registre', Length('registre') - 5, 6)  # Extraer los últimos 6 dígitos
        ).filter(
            registre_suffix=start
        )
    elif exact:
        # Buscar por código específico exacto
        exemplars = exemplars.filter(registre=exact)

    # Formatear los resultados
    results = []
    for exemplar in exemplars:
        tipus = "indefinit"
        if hasattr(exemplar.cataleg, "llibre"):
            tipus = "llibre"
        elif hasattr(exemplar.cataleg, "revista"):
            tipus = "revista"
        elif hasattr(exemplar.cataleg, "cd"):
            tipus = "cd"
        elif hasattr(exemplar.cataleg, "dvd"):
            tipus = "dvd"
        elif hasattr(exemplar.cataleg, "br"):
            tipus = "br"
        elif hasattr(exemplar.cataleg, "dispositiu"):
            tipus = "dispositiu"

        results.append({
            "id": exemplar.id,
            "registre": exemplar.registre,
            "titol": exemplar.cataleg.titol,
            "autor": exemplar.cataleg.autor,
            "editorial": exemplar.cataleg.llibre.editorial if hasattr(exemplar.cataleg, "llibre") else None,
            "tipus": tipus,
            "exclos_prestec": exemplar.exclos_prestec,
            "baixa": exemplar.baixa,
        })

    return results


# Endpoint para obtener sugerencias de búsqueda
@api.get("/cataleg/search/suggestions/", response=List[SearchSuggestionOut])
def get_search_suggestions(request, q: str):
    # Si la consulta está vacía, devolver una lista vacía
    if not q:
        return []
    
    # Buscar en el catálogo
    query = Q(titol__icontains=q) | Q(autor__icontains=q)
    items = Cataleg.objects.filter(query)[:10]  # Limitamos a 10 sugerencias
    
    results = []
    for item in items:
        # Determinar el tipo de ítem
        if hasattr(item, 'llibre'):
            tipus = "llibre"
        elif hasattr(item, 'revista'):
            tipus = "revista"
        elif hasattr(item, 'cd'):
            tipus = "cd"
        elif hasattr(item, 'dvd'):
            tipus = "dvd"
        elif hasattr(item, 'br'):
            tipus = "br"
        elif hasattr(item, 'dispositiu'):
            tipus = "dispositiu"
        else:
            tipus = "indefinit"
        
        results.append({
            "id": item.id,
            "titol": item.titol,
            "autor": item.autor,
            "tipus": tipus
        })
    
    return results

# Endpoint para realizar búsqueda completa
@api.get("/cataleg/search/", response=List[SearchResultOut])
def search_catalog(request, q: str = None):
    # Si la consulta está vacía, devolver todos los elementos del catálogo
    if q is None or q.strip() == '':
        items = Cataleg.objects.all()
    else:
        # Realizar la búsqueda en el catálogo
        query = Q(titol__icontains=q) | Q(autor__icontains=q)
        items = Cataleg.objects.filter(query)
    
    results = []
    for item in items:
        # Base data common to all types
        result = {
            "id": item.id,
            "titol": item.titol,
            "titol_original": item.titol_original,
            "autor": item.autor,
            "CDU": item.CDU,
            "signatura": item.signatura,
            "data_edicio": item.data_edicio.isoformat() if item.data_edicio else None,
            "resum": item.resum,
            "anotacions": item.anotacions,
            "mides": item.mides,
            "tipus": "indefinit"
        }
        
        exemplars = Exemplar.objects.filter(cataleg=item)
        exemplar_counts = {
            "disponible": exemplars.filter(exclos_prestec=False, baixa=False).count(),
            "exclos_prestec": exemplars.filter(exclos_prestec=True, baixa=False).count(),
            "baixa": exemplars.filter(baixa=True).count()
        }
        
        result["exemplar_counts"] = exemplar_counts
        
        # Add tags (categories)
        result["tags"] = [{
            "id": tag.id,
            "nom": tag.nom
        } for tag in item.tags.all()]
        
        # Determine specific type and add specific attributes
        if hasattr(item, 'llibre'):
            llibre = item.llibre
            result["tipus"] = "llibre"
            result["editorial"] = llibre.editorial
            result["ISBN"] = llibre.ISBN
            result["colleccio"] = llibre.colleccio
            result["lloc"] = llibre.lloc
            result["pagines"] = llibre.pagines
            
            # Add país and llengua references
            if llibre.pais:
                result["pais"] = {"id": llibre.pais.id, "nom": llibre.pais.nom}
            
            if llibre.llengua:
                result["llengua"] = {"id": llibre.llengua.id, "nom": llibre.llengua.nom}
            
        elif hasattr(item, 'revista'):
            revista = item.revista
            result["tipus"] = "revista"
            result["editorial"] = revista.editorial
            result["ISSN"] = revista.ISSN
            result["lloc"] = revista.lloc
            result["pagines"] = revista.pagines
            
            # Add país and llengua references
            if revista.pais:
                result["pais"] = {"id": revista.pais.id, "nom": revista.pais.nom}
            
            if revista.llengua:
                result["llengua"] = {"id": revista.llengua.id, "nom": revista.llengua.nom}
            
        elif hasattr(item, 'cd'):
            cd = item.cd
            result["tipus"] = "cd"
            result["discografica"] = cd.discografica
            result["estil"] = cd.estil
            result["duracio"] = str(cd.duracio) if cd.duracio else None
            
        elif hasattr(item, 'dvd'):
            dvd = item.dvd
            result["tipus"] = "dvd"
            result["productora"] = dvd.productora
            result["duracio"] = str(dvd.duracio) if dvd.duracio else None
            
        elif hasattr(item, 'br'):
            br = item.br
            result["tipus"] = "br"
            result["productora"] = br.productora
            result["duracio"] = str(br.duracio) if br.duracio else None
            
        elif hasattr(item, 'dispositiu'):
            dispositiu = item.dispositiu
            result["tipus"] = "dispositiu"
            result["marca"] = dispositiu.marca
            result["model"] = dispositiu.model
        
        # Check if there are exemplars and get their status
        exemplars = Exemplar.objects.filter(cataleg=item)
        if exemplars.exists():
            exemplar = exemplars.first()
            result["exclos_prestec"] = exemplar.exclos_prestec
            result["baixa"] = exemplar.baixa
        
        results.append(result)
    
    return results
# Autenticació bàsica
class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        user = authenticate(username=username, password=password)
        if user:
            # Genera un token simple
            token = secrets.token_hex(16)
            user.auth_token = token
            user.save()
            return token
        return None

# Autenticació per Token Bearer
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            user = Usuari.objects.get(auth_token=token)
            return user
        except Usuari.DoesNotExist:
            return None

# Endpoint per obtenir un token
@api.get("/token", auth=BasicAuth())
@api.get("/token/", auth=BasicAuth())
def obtenir_token(request):
    return {"token": request.auth}


# Endpoint per obtenir dades d'un usuari a partir del seu token
@api.get("/usuari", auth=AuthBearer())
@api.get("/usuari/", auth=AuthBearer())
def obtenir_usuari(request):    
    user = request.auth
    if user:
        user_permissions = [{"id": perm.id, "name": perm.name} for perm in user.user_permissions.all()]
        
        imatge_url = user.imatge.url if user.imatge else None 
        
        return {
            "id": user.id if user else None,
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
            "last_name": user.last_name if user else None,
            "email": user.email if user else None,
            "telefon": user.telefon if user else None,
            "is_staff": user.is_staff if user else None,
            "is_superuser": user.is_superuser if user else None,
            "user_permissions": user_permissions if user else None,
            "centre": {
                "id": user.centre.id,
                "nom": user.centre.nom
            } if user.centre else None,
            "grup": user.grup.nom if user.grup else None,
            "imatge": imatge_url,
        }
    
    return {"error": "Usuari no trobat"}, 404


#  EDITAR USUARI:
from ninja import Schema, File
from ninja.files import UploadedFile

class EditUsuariIn(Schema):
    id: int
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    telefon: Optional[str]

@api.post("/editUsuari/")
def edit_usuari(request, payload: EditUsuariIn, imatge: Optional[UploadedFile] = File(None)):
    try:
        user = Usuari.objects.get(id=payload.id)

        if payload.email and payload.email != user.email:
            user.email = payload.email
        if payload.first_name and payload.first_name != user.first_name:
            user.first_name = payload.first_name
        if payload.last_name and payload.last_name != user.last_name:
            user.last_name = payload.last_name
        if payload.telefon and payload.telefon != user.telefon:
            user.telefon = payload.telefon
        if imatge:
            user.imatge.save(imatge.name, imatge)

        user.save()
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "telefon": user.telefon,
            "imatge": user.imatge.url if user.imatge else None
        }
    except Usuari.DoesNotExist:
        return {"error": "Usuari no trobat"}, 404
    except Exception as e:
        return {"error": str(e)}, 400



# Endpoint per obtenir els préstecs d'un usuari, donat el usuari
@api.get("/usuari/historial_prestecs", auth=AuthBearer())
def get_historial_prestecs_usuari(request, usuari_id: int):
    try:
        # Verificar que el usuario solo puede ver su propio historial
        if request.auth.id != usuari_id:
            return {"error": "No autoritzat"}, 403

        user = Usuari.objects.get(id=usuari_id)
        prestecs = Prestec.objects.filter(usuari=user).select_related('exemplar__cataleg')

        if not prestecs:
            return []

        historial = []
        for prestec in prestecs:
            try:
                exemplar = prestec.exemplar
                if not exemplar:
                    continue
                    
                cataleg = exemplar.cataleg
                if not cataleg:
                    continue

                # Determinar el tipus del catàleg
                tipus = "Indefinit"
                tipus_map = {
                    "cd": "CD",
                    "dvd": "DVD", 
                    "br": "BluRay",
                    "llibre": "Llibre",
                    "revista": "Revista",
                    "dispositiu": "Dispositiu"
                }
                
                for t in tipus_map.keys():
                    if hasattr(cataleg, t):
                        tipus = tipus_map[t]
                        break

                prestec_dict = {
                    "prestec_id": prestec.id,
                    "data_prestec": prestec.data_prestec.isoformat() if prestec.data_prestec else None,
                    "data_devolucio": prestec.data_retorn.isoformat() if prestec.data_retorn else None,  # Cambiar a data_retorn
                    "exemplar": {
                        "id": exemplar.id,
                        "registre": exemplar.registre,
                        "cataleg": {
                            "id": cataleg.id,
                            "titol": cataleg.titol,
                            "autor": cataleg.autor,
                            "tipus": tipus
                        }
                    }
                }
                historial.append(prestec_dict)
            except Exception:
                continue

        return historial

    except Usuari.DoesNotExist:
        return {"error": "Usuari no trobat"}, 404
    except Exception as e:
        return {"error": str(e)}, 400


class CatalegOut(Schema):
    id: int
    titol: str
    autor: Optional[str]

class LlibreOut(CatalegOut):
    editorial: Optional[str]
    ISBN: Optional[str]

class ExemplarOut(Schema):
    id: int
    registre: str
    exclos_prestec: bool
    baixa: bool
    cataleg: Union[LlibreOut,CatalegOut]
    tipus: str

class LlibreIn(Schema):
    titol: str
    editorial: str


@api.get("/llibres", response=List[LlibreOut])
@api.get("/llibres/", response=List[LlibreOut])
#@api.get("/llibres/", response=List[LlibreOut], auth=AuthBearer())
def get_llibres(request):
    qs = Llibre.objects.all()
    return qs

@api.post("/llibres/")
def post_llibres(request, payload: LlibreIn):
    llibre = Llibre.objects.create(**payload.dict())
    return {
        "id": llibre.id,
        "titol": llibre.titol
    }

@api.get("/exemplars", response=List[ExemplarOut])
@api.get("/exemplars/", response=List[ExemplarOut])
def get_exemplars(request):
    # carreguem objectes amb els proxy models relacionats exactes
    exemplars = Exemplar.objects.select_related(
        "cataleg__llibre",
        "cataleg__revista",
        "cataleg__cd",
        "cataleg__dvd",
        "cataleg__br",
        "cataleg__dispositiu",
    ).all()
    result = []

    for exemplar in exemplars:
        cataleg_instance = exemplar.cataleg

        # Determinar el tipus de l'objecte Cataleg
        if hasattr(cataleg_instance, "llibre"):
            cataleg_schema = LlibreOut.from_orm(cataleg_instance.llibre)
            tipus = "llibre"
        #elif hasattr(cataleg_instance, "dispositiu"):
        #    cataleg_schema = LlibreOut.from_orm(cataleg_instance.dispositiu)
        # TODO: afegir altres esquemes
        else:
            cataleg_schema = CatalegOut.from_orm(cataleg_instance)
            tipus = "indefinit"

        # Afegir l'Exemplar amb el Cataleg serialitzat
        result.append(
            ExemplarOut(
                id=exemplar.id,
                registre=exemplar.registre,
                exclos_prestec=exemplar.exclos_prestec,
                baixa=exemplar.baixa,
                cataleg=cataleg_schema,
                tipus=tipus,
            )
        )

    return result

# Schema for exemplars by catalog item
class ExemplarItemOut(Schema):
    id: int
    registre: str
    exclos_prestec: bool
    baixa: bool
    centre: Optional[dict] = None  # Añadir centro
    cataleg: Optional[dict] = None  # Añadir catálogo para mostrar título y autor

# 2. Actualizar el endpoint get_exemplars_by_item para incluir esta información
@api.get("/exemplars/by-item/{item_id}", response=List[ExemplarItemOut])
def get_exemplars_by_item_public(request, item_id: int):
    """
    Endpoint público para obtener ejemplares por ítem para mostrar disponibilidad por centro
    No requiere autenticación
    """
    exemplars = Exemplar.objects.filter(
        cataleg_id=item_id
    ).select_related('centre', 'cataleg')
    
    result = []
    for exemplar in exemplars:
        result.append({
            "id": exemplar.id,
            "registre": exemplar.registre,
            "exclos_prestec": exemplar.exclos_prestec,
            "baixa": exemplar.baixa,
            "centre": {
                "id": exemplar.centre.id,
                "nom": exemplar.centre.nom
            } if exemplar.centre else None,
            "cataleg": {
                "id": exemplar.cataleg.id,
                "titol": exemplar.cataleg.titol,
                "autor": exemplar.cataleg.autor
            } if exemplar.cataleg else None
        })
    
    return result

# Schema for users list (for loan creation)
class UserOut(Schema):
    id: int
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    centre: Optional[str]

# Schema for loan creation
class LoanCreateIn(Schema):
    usuari_id: int
    exemplar_id: int
    anotacions: Optional[str] = None

class LoanCreateOut(Schema):
    id: int
    usuari: UserOut
    exemplar: ExemplarItemOut
    data_prestec: str
    mensaje: str = "Préstamo creado correctamente"

# Get exemplar details by ID
@api.get("/exemplars/{exemplar_id}/", response=ExemplarItemOut, auth=AuthBearer())
def get_exemplar_by_id(request, exemplar_id: int):
    user = request.auth
    if not user:
        return {"error": "No autorizado"}, 401
    
    try:
        exemplar = Exemplar.objects.select_related('centre', 'cataleg').get(id=exemplar_id)
        return {
            "id": exemplar.id,
            "registre": exemplar.registre,
            "exclos_prestec": exemplar.exclos_prestec,
            "baixa": exemplar.baixa,
            "centre": {
                "id": exemplar.centre.id,
                "nom": exemplar.centre.nom
            } if exemplar.centre else None,
            "cataleg": {
                "id": exemplar.cataleg.id,
                "titol": exemplar.cataleg.titol,
                "autor": exemplar.cataleg.autor
            } if exemplar.cataleg else None
        }
    except Exemplar.DoesNotExist:
        return {"error": "Ejemplar no encontrado"}, 404

# Get available users for loans
@api.get("/usuarios-disponibles/", response=List[UserOut], auth=AuthBearer())
def get_available_users(request):
    user = request.auth
    if not user or not user.is_staff:
        return {"error": "No autorizado"}, 401
    
    # Obtener todos los usuarios activos, sin filtrar por centro
    users = Usuari.objects.filter(is_active=True)
    
    result = []
    for u in users:
        # No incluir al propio bibliotecario ni a otros usuarios staff
        if u.id != user.id and not u.is_staff:
            result.append({
                "id": u.id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "centre": u.centre.nom if u.centre else None
            })
    
    return result

# Create a new loan
@api.post("/prestecs/crear/", response=LoanCreateOut, auth=AuthBearer())
def create_loan(request, payload: LoanCreateIn):
    bibliotecari = request.auth
    if not bibliotecari or not bibliotecari.is_staff:
        return {"error": "No autorizado"}, 401
    
    try:
        # Obtener el usuario y ejemplar
        usuario = Usuari.objects.get(id=payload.usuari_id)
        exemplar = Exemplar.objects.get(id=payload.exemplar_id)
        
        # Verificar que el ejemplar está disponible
        if exemplar.exclos_prestec:
            return {"error": "El ejemplar está excluido de préstamo"}, 400
        if exemplar.baixa:
            return {"error": "El ejemplar está dado de baja"}, 400
        
        # Reforzar validación de centro: un bibliotecario solo puede prestar ejemplares de su centro
        if not bibliotecari.centre:
            return {"error": "El bibliotecario no tiene un centro asignado"}, 400
            
        if not exemplar.centre:
            return {"error": "El ejemplar no tiene un centro asignado"}, 400
            
        # Comparar los IDs de los centros, no las instancias
        if bibliotecari.centre.id != exemplar.centre.id and not bibliotecari.is_superuser:
            return {"error": f"El ejemplar pertenece al centre '{exemplar.centre.nom}' y tú perteneces a '{bibliotecari.centre.nom}'"}, 400
        
        # Crear el préstamo
        prestec = Prestec.objects.create(
            usuari=usuario,
            exemplar=exemplar,
            anotacions=payload.anotacions
        )
        
        # Marcar el ejemplar como excluido de préstamo
        exemplar.exclos_prestec = True
        exemplar.save()
        
        # Registrar en el log
        Log.objects.create(
            usuari=bibliotecari.username,
            accio=f"Préstamo creado: ID {prestec.id} - Ejemplar {exemplar.registre} a {usuario.username}",
            tipus="INFO"
        )
        
        # Devolver resultado
        return {
            "id": prestec.id,
            "usuari": {
                "id": usuario.id,
                "username": usuario.username,
                "first_name": usuario.first_name,
                "last_name": usuario.last_name,
                "email": usuario.email,
                "centre": usuario.centre.nom if usuario.centre else None
            },
            "exemplar": {
                "id": exemplar.id,
                "registre": exemplar.registre,
                "exclos_prestec": exemplar.exclos_prestec,
                "baixa": exemplar.baixa,
                "centre": {
                    "id": exemplar.centre.id,
                    "nom": exemplar.centre.nom
                } if exemplar.centre else None
            },
            "data_prestec": prestec.data_prestec.isoformat()
        }
        
    except Usuari.DoesNotExist:
        return {"error": "Usuario no encontrado"}, 404
    except Exemplar.DoesNotExist:
        return {"error": "Ejemplar no encontrado"}, 404
    except Exception as e:
        # Registrar error en el log
        Log.objects.create(
            usuari=bibliotecari.username,
            accio=f"Error al crear préstamo: {str(e)}",
            tipus="ERROR"
        )
        return {"error": f"Error al crear el préstamo: {str(e)}"}, 500

# Nuevos endpoints para autocompletar autores y editoriales
@api.get("/autores/search/")
def buscar_autores(request, q: str):
    """Busca autores en la base de datos y en Google Books si es necesario"""
    q = q.strip()
    # Primero buscar en nuestra base de datos - ordenamos para priorizar los que empiezan por el texto
    # Creamos dos queries: una para los que empiezan por el texto y otra para los que lo contienen
    resultados_db_starts = Llibre.objects.filter(autor__istartswith=q).values('autor').distinct()
    resultados_db_contains = Llibre.objects.filter(autor__icontains=q).exclude(autor__istartswith=q).values('autor').distinct()
    
    # Combinamos los resultados, primero los que empiezan por el texto
    autores_starts = [item['autor'] for item in resultados_db_starts if item['autor']]
    autores_contains = [item['autor'] for item in resultados_db_contains if item['autor']]
    
    # Usamos un diccionario para eliminar duplicados preservando el orden
    autores_dict = {}
    for autor in autores_starts + autores_contains:
        # Usamos el nombre en minúsculas como clave para evitar duplicados por mayúsculas/minúsculas
        autores_dict[autor.lower()] = autor
    
    autores = list(autores_dict.values())
    
    # Si no hay suficientes resultados (menos de 5), buscamos en Google Books
    if len(autores) < 5:
        try:
            import requests
            response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=inauthor:{q}&maxResults=10")
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    # Lista temporal para ordenar los resultados de Google Books
                    google_autores_start = []
                    google_autores_contain = []
                    
                    for item in data['items']:
                        if 'volumeInfo' in item and 'authors' in item['volumeInfo']:
                            for autor in item['volumeInfo']['authors']:
                                if autor and autor.lower() not in autores_dict:
                                    # Verificamos si el autor comienza con el texto buscado
                                    if autor.lower().startswith(q.lower()):
                                        google_autores_start.append(autor)
                                    else:
                                        google_autores_contain.append(autor)
                                    # Agregamos al diccionario para evitar duplicados en siguientes iteraciones
                                    autores_dict[autor.lower()] = autor
                    
                    # Añadimos los autores de Google Books a nuestra lista, primero los que empiezan por q
                    autores.extend(google_autores_start)
                    autores.extend(google_autores_contain)
        except Exception as e:
            print(f"Error al buscar en Google Books: {e}")
    
    return {"resultados": autores[:10]}  # Devolvemos máximo 10 resultados

@api.get("/editoriales/search/")
def buscar_editoriales(request, q: str):
    """Busca editoriales en la base de datos y en Google Books si es necesario"""
    q = q.strip()
    # Primero buscar en nuestra base de datos - ordenamos para priorizar las que empiezan por el texto
    resultados_db_starts = Llibre.objects.filter(editorial__istartswith=q).values('editorial').distinct()
    resultados_db_contains = Llibre.objects.filter(editorial__icontains=q).exclude(editorial__istartswith=q).values('editorial').distinct()
    
    # Combinamos los resultados, primero los que empiezan por el texto
    editoriales_starts = [item['editorial'] for item in resultados_db_starts if item['editorial']]
    editoriales_contains = [item['editorial'] for item in resultados_db_contains if item['editorial']]
    
    # Usamos un diccionario para eliminar duplicados preservando el orden
    editoriales_dict = {}
    for editorial in editoriales_starts + editoriales_contains:
        # Usamos el nombre en minúsculas como clave para evitar duplicados por mayúsculas/minúsculas
        editoriales_dict[editorial.lower()] = editorial
    
    editoriales = list(editoriales_dict.values())
    
    # Si no hay suficientes resultados (menos de 5), buscamos en Google Books
    if len(editoriales) < 5:
        try:
            import requests
            response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=inpublisher:{q}&maxResults=10")
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    # Lista temporal para ordenar los resultados de Google Books
                    google_editoriales_start = []
                    google_editoriales_contain = []
                    
                    for item in data['items']:
                        if 'volumeInfo' in item and 'publisher' in item['volumeInfo']:
                            publisher = item['volumeInfo']['publisher']
                            if publisher and publisher.lower() not in editoriales_dict:
                                # Verificamos si la editorial comienza con el texto buscado
                                if publisher.lower().startswith(q.lower()):
                                    google_editoriales_start.append(publisher)
                                else:
                                    google_editoriales_contain.append(publisher)
                                # Agregamos al diccionario para evitar duplicados en siguientes iteraciones
                                editoriales_dict[publisher.lower()] = publisher
                    
                    # Añadimos las editoriales de Google Books a nuestra lista, manteniendo prioridad
                    editoriales.extend(google_editoriales_start)
                    editoriales.extend(google_editoriales_contain)
        except Exception as e:
            print(f"Error al buscar en Google Books: {e}")
    
    return {"resultados": editoriales[:10]}  # Devolvemos máximo 10 resultados

class ExemplarSuggestionOut(Schema):
    id: int
    tipo: str
    resultado: str

@api.get("/exemplars/search/suggestions/", response=List[ExemplarSuggestionOut])
def get_exemplar_suggestions(request, q: str = Query(...)):
    """
    Endpoint para obtener sugerencias de búsqueda de ejemplares.
    """
    if not q:
        return []

    # Eliminar signos de puntuación de la consulta
    normalized_query = re.sub(r'[^\w\s]', '', q).lower()

    exemplars = Exemplar.objects.filter(
        Q(cataleg__titol__icontains=normalized_query) |
        Q(cataleg__autor__icontains=normalized_query) |
        Q(cataleg__llibre__editorial__icontains=normalized_query)
    ).select_related("cataleg")[:50]  # Limitar a 50 resultados para optimización

    results = []
    seen_results = set()  # Usar un conjunto para garantizar unicidad

    for exemplar in exemplars:
        if normalized_query in re.sub(r'[^\w\s]', '', exemplar.cataleg.titol).lower():
            result = {
                "id": exemplar.id,
                "tipo": "Título",
                "resultado": exemplar.cataleg.titol,
            }
            if result["resultado"] not in seen_results:
                results.append(result)
                seen_results.add(result["resultado"])

        if exemplar.cataleg.autor and normalized_query in re.sub(r'[^\w\s]', '', exemplar.cataleg.autor).lower():
            result = {
                "id": exemplar.id,
                "tipo": "Autor",
                "resultado": exemplar.cataleg.autor,
            }
            if result["resultado"] not in seen_results:
                results.append(result)
                seen_results.add(result["resultado"])

        if hasattr(exemplar.cataleg, "llibre") and exemplar.cataleg.llibre.editorial:
            editorial_normalized = re.sub(r'[^\w\s]', '', exemplar.cataleg.llibre.editorial).lower()
            if normalized_query in editorial_normalized:
                result = {
                    "id": exemplar.id,
                    "tipo": "Editorial",
                    "resultado": exemplar.cataleg.llibre.editorial,
                }
                if result["resultado"] not in seen_results:
                    results.append(result)
                    seen_results.add(result["resultado"])

    return results
