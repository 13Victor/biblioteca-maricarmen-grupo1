from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from biblioteca.models import *
from faker import Faker
import random
from datetime import datetime, timedelta
import os

class Command(BaseCommand):
    help = 'Seeds the database with sample data'

    def handle(self, *args, **kwargs):
        fake = Faker(['es_ES'])
        self.stdout.write('Seeding database...')

        # Clean existing data
        self.stdout.write('Cleaning existing data...')
        Prestec.objects.all().delete()
        Reserva.objects.all().delete()
        Exemplar.objects.all().delete()
        Llibre.objects.all().delete()
        Usuari.objects.filter(is_superuser=False).delete()
        Categoria.objects.all().delete()
        Pais.objects.all().delete()
        Llengua.objects.all().delete()
        Centre.objects.all().delete()
        Cicle.objects.all().delete()

        # Create basic data
        self.stdout.write('Creating countries...')
        paisos = ['España', 'Francia', 'Reino Unido', 'Estados Unidos', 'Alemania']
        pais_objects = [Pais.objects.create(nom=pais) for pais in paisos]

        self.stdout.write('Creating languages...')
        llengues = ['Català', 'Castellano', 'English', 'Français', 'Deutsch']
        llengua_objects = [Llengua.objects.create(nom=llengua) for llengua in llengues]

        self.stdout.write('Creating categories...')
        categories = ['Novel·la', 'Poesia', 'Història', 'Ciència', 'Art', 'Tecnologia']
        categoria_objects = [Categoria.objects.create(nom=cat) for cat in categories]

        self.stdout.write('Creating centers and cycles...')
        centres = [Centre.objects.create(nom=f"Centre {i}") for i in range(1, 6)]
        cicles = [Cicle.objects.create(nom=f"Cicle {i}") for i in range(1, 6)]

        # Create users
        self.stdout.write('Creating users...')
        num_users = random.randint(200, 300)
        users = []
        for _ in range(num_users):
            user = Usuari.objects.create(
                username=fake.user_name(),
                email=fake.email(),
                password=make_password('password123'),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                telefon=fake.numerify('#########'),
                centre=random.choice(centres),
                cicle=random.choice(cicles)
            )
            users.append(user)

        # Create books and authors
        self.stdout.write('Creating books and authors...')
        fake_en = Faker('en_US')  # English faker for book-related data
        llibres = []
        
        for _ in range(100):
            author = fake_en.name()  # Usando name() para autores más realistas
            num_books = random.randint(1, 5)
            
            for _ in range(num_books):
                # CDU generation
                cdu_base = random.choice(['0', '1', '2', '3', '5', '6', '7', '8', '9'])
                cdu_sub = random.randint(0, 99)
                cdu = f"{cdu_base}{cdu_sub:02d}"
                
                llibre = Llibre.objects.create(
                    # Campos heredados de Cataleg
                    titol=fake_en.catch_phrase(),
                    titol_original=fake_en.catch_phrase() if random.random() > 0.7 else None,
                    autor=author,
                    CDU=cdu,
                    signatura=f"{cdu}/{author.split()[0][:3].upper()}",
                    data_edicio=fake.date_between(start_date='-20y', end_date='now'),
                    resum=fake.paragraph(nb_sentences=5),
                    anotacions=fake.paragraph(nb_sentences=2) if random.random() > 0.7 else None,
                    mides=f"{random.randint(15,30)}x{random.randint(10,25)} cm",
                    
                    # Campos específicos de Llibre
                    ISBN=fake_en.isbn13(),
                    editorial=fake_en.company(),
                    colleccio=fake_en.sentence(nb_words=2) if random.random() > 0.5 else None,
                    lloc=fake.city(),
                    pais=random.choice(pais_objects),
                    llengua=random.choice(llengua_objects),
                    numero=random.randint(1, 10) if random.random() > 0.7 else None,
                    volums=random.randint(1, 5) if random.random() > 0.8 else None,
                    pagines=random.randint(50, 1000),
                )
                
                # Asignar entre 1 y 3 categorías aleatorias
                num_categories = random.randint(1, 3)
                categories_to_add = random.sample(list(categoria_objects), num_categories)
                llibre.tags.set(categories_to_add)
                
                llibres.append(llibre)

        # Create exemplars
        self.stdout.write('Creating exemplars...')
        exemplars = []
        for _ in range(5000):
            llibre = random.choice(llibres)
            exemplar = Exemplar.objects.create(
                cataleg=llibre,
                registre=fake.unique.bothify(text='REG-#####'),
                exclos_prestec=random.random() < 0.1,
                baixa=random.random() < 0.05
            )
            exemplars.append(exemplar)

        # Create loans and reservations
        self.stdout.write('Creating loans and reservations...')
        available_exemplars = [e for e in exemplars if not e.exclos_prestec and not e.baixa]
        
        # Create active loans
        for _ in range(200):
            if not available_exemplars:
                break
            exemplar = random.choice(available_exemplars)
            available_exemplars.remove(exemplar)
            Prestec.objects.create(
                usuari=random.choice(users),
                exemplar=exemplar,
                data_prestec=fake.date_between(start_date='-30d', end_date='now'),
            )

        # Create historical loans
        for _ in range(1000):
            exemplar = random.choice(exemplars)
            data_prestec = fake.date_between(start_date='-1y', end_date='-1d')
            Prestec.objects.create(
                usuari=random.choice(users),
                exemplar=exemplar,
                data_prestec=data_prestec,
                data_retorn=data_prestec + timedelta(days=random.randint(1, 30))
            )

        # Create reservations
        for _ in range(100):
            Reserva.objects.create(
                usuari=random.choice(users),
                exemplar=random.choice(exemplars)
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded database'))
