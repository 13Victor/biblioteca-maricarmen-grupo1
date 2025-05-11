from django.contrib.auth import authenticate
from ninja import NinjaAPI, Schema
from ninja.security import HttpBasicAuth, HttpBearer
from .models import *
from typing import List, Optional, Union, Literal
import secrets
from django.db.models import Q

from ninja import Router
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64

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
@api.get("/token/")
def get_token(request):
    """
    Endpoint para obtener un token de autenticación.
    Soporta autenticación básica (usuario/contraseña) y social (token).
    """
    # Verificar si viene de autenticación social (token en parámetro)
    social_token = request.GET.get('social_token')
    if social_token:
        try:
            usuario = Usuari.objects.get(auth_token=social_token)
            # Si el usuario existe con ese token, autenticarlo
            return JsonResponse({
                'token': social_token,
                'user': {
                    'id': usuario.id,
                    'username': usuario.username,
                    'email': usuario.email,
                    'is_staff': usuario.is_staff,
                    'is_superuser': usuario.is_superuser,
                    'first_name': usuario.first_name or "",
                    'last_name': usuario.last_name or "",
                }
            })
        except Usuari.DoesNotExist:
            return JsonResponse({'error': 'Token inválido'}, status=401)
    
    # Autenticación básica (usuario/contraseña)
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Basic '):
        return JsonResponse({'error': 'Se requiere autenticación básica'}, status=401)
    
    try:
        # Decodificar credenciales
        auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = auth_decoded.split(':', 1)
        
        # Autenticar usuario
        user = authenticate(username=username, password=password)
        if user is None:
            return JsonResponse({'error': 'Credenciales inválidas'}, status=401)
        
        # Si el usuario no tiene token, generarlo
        if not hasattr(user, 'auth_token') or not user.auth_token:
            from django.utils.crypto import get_random_string
            user.auth_token = get_random_string(32)
            user.save()
        
        # Return token AND basic user info
        return JsonResponse({
            'token': user.auth_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'first_name': user.first_name or "",
                'last_name': user.last_name or ""
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Endpoint per obtenir dades d'un usuari a partir del seu token
@api.get("/usuari", auth=AuthBearer())
@api.get("/usuari/", auth=AuthBearer())
def obtenir_usuari(request):    
    user = request.auth
    if user:
        # Include all user permissions
        user_permissions = [{"id": perm.id, "name": perm.name} for perm in user.user_permissions.all()]
        
        # Handle image URL safely
        imatge_url = user.imatge.url if hasattr(user, 'imatge') and user.imatge else None
        
        # Return a complete user object with all needed fields
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "user_permissions": user_permissions,
            "centre": user.centre.nom if hasattr(user, 'centre') and user.centre else None,
            "cicle": user.cicle.nom if hasattr(user, 'cicle') and user.cicle else None,
            "telefon": user.telefon if hasattr(user, 'telefon') else None,
            "grup": user.grup if hasattr(user, 'grup') else None,
            "imatge": imatge_url,
            # Add any other fields your frontend needs
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
        if imatge:
            user.imatge.save(imatge.name, imatge)

        user.save()
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "imatge": user.imatge.url if user.imatge else None
        }
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
@api.get("/exemplars/by-item/{item_id}/", response=List[ExemplarItemOut], auth=AuthBearer())
def get_exemplars_by_item(request, item_id: int):
    user = request.auth
    if not user or not user.centre:
        return []
    
    exemplars = Exemplar.objects.filter(
        cataleg_id=item_id,
        centre=user.centre
    ).select_related('centre', 'cataleg')  # Incluir relaciones
    
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
        
        # Verificar que el ejemplar pertenece al centro del bibliotecario
        # Mantenemos esta validación para que un bibliotecario solo pueda prestar ejemplares de su centro
        if bibliotecari.centre != exemplar.centre and not bibliotecari.is_superuser:
            return {"error": "El ejemplar no pertenece a tu centro"}, 400
        
        # ELIMINADO: Ya no verificamos que el usuario pertenezca al centro del bibliotecario
        
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
                "exclos_prestec": exemplar.exclos_prestec,  # Ahora será True
                "baixa": exemplar.baixa
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
