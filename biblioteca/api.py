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
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "telefon": user.telefon,  # Añadido el campo telefon
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "user_permissions": user_permissions,
            "centre": user.centre.nom if user.centre else None,
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
