from django.contrib.auth import authenticate
from ninja import NinjaAPI, Schema
from ninja.security import HttpBasicAuth, HttpBearer
from .models import *
from typing import List, Optional, Union, Literal
import secrets
from django.db.models import Q

api = NinjaAPI()


class SearchSuggestionOut(Schema):
    id: int
    titol: str
    autor: Optional[str]
    tipus: str

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
        #pasar 'user_permissions' en una lista de diccionarios
        user_permissions = [{"id": perm.id, "name": perm.name} for perm in user.user_permissions.all()]
        
        imatge_url = user.imatge.url if user.imatge else None 
        
        #respuesta json
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "user_permissions": user_permissions,
            "centre": user.centre,
            "cicle": user.cicle,
            "imatge": imatge_url,
        }
    
    return {"error": "Usuari no trobat"}, 404







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
