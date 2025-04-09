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
    autor: Optional[str]
    tipus: str
    editorial: Optional[str] = None
    ISBN: Optional[str] = None
    ISSN: Optional[str] = None
    exclos_prestec: Optional[bool] = None
    baixa: Optional[bool] = None

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
        # Base de datos común para todos los tipos
        result = {
            "id": item.id,
            "titol": item.titol,
            "autor": item.autor,
            "tipus": "indefinit"
        }
        
        # Determinar tipo específico y añadir atributos específicos
        if hasattr(item, 'llibre'):
            result["tipus"] = "llibre"
            result["editorial"] = item.llibre.editorial
            result["ISBN"] = item.llibre.ISBN
        elif hasattr(item, 'revista'):
            result["tipus"] = "revista"
            result["editorial"] = item.revista.editorial
            result["ISSN"] = item.revista.ISSN
        elif hasattr(item, 'cd'):
            result["tipus"] = "cd"
            result["discografica"] = item.cd.discografica
            result["estil"] = item.cd.estil
        elif hasattr(item, 'dvd'):
            result["tipus"] = "dvd"
            result["productora"] = item.dvd.productora
        elif hasattr(item, 'br'):
            result["tipus"] = "br"
            result["productora"] = item.br.productora
        elif hasattr(item, 'dispositiu'):
            result["tipus"] = "dispositiu"
            result["marca"] = item.dispositiu.marca
            result["model"] = item.dispositiu.model
        
        # Comprobar si hay ejemplares y su estado
        exemplars = Exemplar.objects.filter(cataleg=item)
        if exemplars.exists():
            exemplar = exemplars.first()
            result["exclos_prestec"] = exemplar.exclos_prestec
            result["baixa"] = exemplar.baixa
        
        results.append(result)
    
    return results  # Faltaba este return
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
