from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from django.contrib.auth.hashers import make_password
import re

class Categoria(models.Model):
    class Meta:
        verbose_name_plural = "Categories"
    nom = models.CharField(max_length=100)
    parent = models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True)
    def __str__(self):
        return self.nom

class Pais(models.Model):
    class Meta:
        verbose_name_plural = "Països"
    nom = models.CharField(max_length=200)
    def __str__(self):
        return self.nom

class Llengua(models.Model):
    class Meta:
        verbose_name_plural = "Llengües"
    nom = models.CharField(max_length=200)
    def __str__(self):
        return self.nom

class Cataleg(models.Model):
    titol = models.CharField(max_length=200)
    titol_original = models.CharField(max_length=200, blank=True, null=True)
    autor = models.CharField(max_length=200, blank=True, null=True)
    CDU = models.CharField(max_length=40, blank=True, null=True)
    signatura = models.CharField(max_length=40, blank=True, null=True)
    data_edicio = models.DateField(null=True,blank=True)
    resum = models.TextField(blank=True,null=True)
    anotacions = models.TextField(blank=True,null=True)
    mides = models.CharField(max_length=100,null=True,blank=True)
    tags = models.ManyToManyField(Categoria,blank=True)
    def exemplars(self):
    	return 0
    def __str__(self):
        return self.titol

class Llibre(Cataleg):
    ISBN = models.CharField(max_length=13, blank=True, null=True)
    editorial = models.CharField(max_length=100, blank=True, null=True)
    colleccio = models.CharField(max_length=100, blank=True, null=True)
    lloc = models.CharField(max_length=100, blank=True, null=True)
    pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, blank=True, null=True)
    llengua = models.ForeignKey(Llengua, on_delete=models.SET_NULL, blank=True, null=True)
    numero = models.IntegerField(null=True,blank=True)
    volums = models.IntegerField(null=True,blank=True)
    pagines = models.IntegerField(blank=True,null=True)
    info_url = models.CharField(max_length=200,blank=True,null=True)
    preview_url = models.CharField(max_length=200,blank=True,null=True)
    thumbnail_url = models.CharField(max_length=200,blank=True,null=True)

class Revista(Cataleg):
    class Meta:
        verbose_name_plural = "Revistes"
    ISSN = models.CharField(max_length=13, blank=True, null=True)
    editorial = models.CharField(max_length=100, blank=True, null=True)
    lloc = models.CharField(max_length=100, blank=True, null=True)
    pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, blank=True, null=True)
    llengua = models.ForeignKey(Llengua, on_delete=models.SET_NULL, blank=True, null=True)
    numero = models.IntegerField(null=True,blank=True)
    volums = models.IntegerField(null=True,blank=True)
    pagines = models.IntegerField(blank=True,null=True)

class CD(Cataleg):
    discografica = models.CharField(max_length=100)
    estil = models.CharField(max_length=100)
    duracio = models.TimeField()

class DVD(Cataleg):
    productora = models.CharField(max_length=100)
    duracio = models.TimeField()

class BR(Cataleg):
    productora = models.CharField(max_length=100)
    duracio = models.TimeField()

class Dispositiu(Cataleg):
    marca = models.CharField(max_length=100)
    model = models.CharField(max_length=100,null=True,blank=True)

# Usuaris i Centre
class Centre(models.Model):
    nom = models.CharField(max_length=200)
    def __str__(self):
        return self.nom

class Grup(models.Model):
    nom = models.CharField(max_length=200)
    def __str__(self):
        return self.nom

class Usuari(AbstractUser):
    telefon = models.CharField(max_length=9,blank=True,null=True)
    centre = models.ForeignKey(Centre,on_delete=models.SET_NULL,null=True,blank=True)  # Centro puede ser null para usuarios normales
    grup = models.ForeignKey(Grup,on_delete=models.SET_NULL,null=True,blank=True)
    imatge = models.ImageField(upload_to='usuaris/',null=True,blank=True)
    auth_token = models.CharField(max_length=32,blank=True,null=True)

    def is_bibliotecari(self):
        return self.groups.filter(name='Bibliotecaris').exists()

    def save(self, *args, **kwargs):
        if self.is_staff and not self.centre and not self.pk:  # solo para nuevos usuarios staff
            raise ValueError("Staff users must have a centre assigned")
        if self.is_staff and not self.centre and self.pk:  # para usuarios existentes
            original = Usuari.objects.get(pk=self.pk)
            if not original.is_staff and self.is_staff:  # solo si se está convirtiendo en staff
                raise ValueError("Staff users must have a centre assigned")
        super().save(*args, **kwargs)

class Exemplar(models.Model):
    cataleg = models.ForeignKey(Cataleg, on_delete=models.CASCADE)
    registre = models.CharField(max_length=100, unique=True, editable=False)
    exclos_prestec = models.BooleanField(default=False)
    baixa = models.BooleanField(default=False)
    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, verbose_name="Centre")

    class Meta:
        verbose_name = "Exemplar"
        verbose_name_plural = "Exemplars"
        ordering = ['registre']

    def __str__(self):
        return f"REG:{self.registre} - {self.cataleg.titol}"

    def save(self, *args, **kwargs):
        if not self.registre:
            year = now().year
            max_num = 0

            last_exemplar = (
                Exemplar.objects
                .filter(registre__regex=r'^EX-\d{4}-\d{6}$')
                .order_by('-registre')
                .only('registre')
                .first()
            )

            if last_exemplar:
                match = re.match(r'EX-\d{4}-(\d{6})', last_exemplar.registre)
                if match:
                    max_num = int(match.group(1))

            nou_numero = max_num + 1
            self.registre = f'EX-{year}-{nou_numero:06d}'

        super().save(*args, **kwargs)


class Imatge(models.Model):
    cataleg = models.ForeignKey(Cataleg, on_delete=models.CASCADE)
    imatge = models.ImageField(upload_to='imatges/')

class Reserva(models.Model):
    class Meta:
        verbose_name_plural = "Reserves"
    usuari = models.ForeignKey(Usuari, on_delete=models.CASCADE)
    exemplar = models.ForeignKey(Exemplar, on_delete=models.CASCADE)
    data = models.DateField(auto_now_add=True)

class Prestec(models.Model):
    class Meta:
        verbose_name_plural = "Préstecs"
    usuari = models.ForeignKey(Usuari, on_delete=models.CASCADE)
    exemplar = models.ForeignKey(Exemplar, on_delete=models.CASCADE)
    data_prestec = models.DateField(auto_now_add=True)
    data_retorn = models.DateField(null=True, blank=True)
    anotacions = models.TextField(blank=True,null=True)
    
    def centre_exemplar(self):
        return self.exemplar.centre
    centre_exemplar.short_description = "Centre"
    
    def __str__(self):
        return str(self.exemplar)

class Peticio(models.Model):
    class Meta:
        verbose_name_plural = "Peticions"
    usuari = models.ForeignKey(Usuari, on_delete=models.CASCADE)
    titol = models.CharField(max_length=200)
    descripcio = models.TextField()
    data = models.DateField(auto_now_add=True)

class Log(models.Model):
    TIPO_LOG = (
        ('INFO', 'Información'),
        ('WARNING', 'Advertencia'),
        ('ERROR', 'Error'),
        ('FATAL', 'Fatal'),
    )
    usuari = models.CharField(max_length=100, null=True, blank=True)
    accio = models.CharField(max_length=100)
    data_accio = models.DateTimeField(auto_now_add=True)
    tipus = models.CharField(max_length=10, choices=TIPO_LOG, default="")

    def __str__(self):
        return f"{self.accio} - {self.tipus}"


