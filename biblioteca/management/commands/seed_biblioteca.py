from django.core.management.base import BaseCommand
from django.utils import timezone
import random
from faker import Faker
from datetime import time, timedelta, datetime
from tqdm import tqdm
from biblioteca.models import (
    Pais, Llengua, Categoria, 
    Llibre, Revista, CD, DVD, BR, Dispositiu, 
    Exemplar, Centre, Cicle, Usuari, Prestec, Reserva
)

class Command(BaseCommand):
    help = 'Seed database with sample data for all catalog types'

    def add_arguments(self, parser):
        parser.add_argument('--autors', type=int, default=100, help='Number of authors to create')
        parser.add_argument('--usuaris', type=int, default=300, help='Number of users to create')
        parser.add_argument('--min-llibres', type=int, default=8, help='Minimum books per author')
        parser.add_argument('--max-llibres', type=int, default=12, help='Maximum books per author')
        parser.add_argument('--revistes', type=int, default=200, help='Number of magazines to create')
        parser.add_argument('--cds', type=int, default=80, help='Number of CDs to create')
        parser.add_argument('--dvds', type=int, default=60, help='Number of DVDs to create')
        parser.add_argument('--brs', type=int, default=40, help='Number of Blu-rays to create')
        parser.add_argument('--dispositius', type=int, default=20, help='Number of devices to create')
        parser.add_argument('--exemplars', type=int, default=5, help='Average number of copies per catalog item')
        parser.add_argument('--delete', action='store_true', help='Delete existing data before creating new objects')
        parser.add_argument('--prestecs', type=int, default=300, help='Number of loans to create')
        parser.add_argument('--reservas', type=int, default=100, help='Number of reservations to create')

    def handle(self, *args, **options):
        fake = Faker(['es_ES'])
        fake_en = Faker(['en_US']) # Para títulos originales en inglés
        
        # Always delete existing data
        self._delete_existing_data()
        
        # Get or create initial data
        llengues, paisos, categories = self._setup_initial_data(fake)
        
        # Create authors first
        autors = self._create_autors(fake, options['autors'])
        
        # Create catalog items by author
        for autor in autors:
            num_llibres = random.randint(options['min_llibres'], options['max_llibres'])
            self._create_llibres_for_autor(fake, fake_en, autor, num_llibres, llengues, paisos, categories, options['exemplars'])
        
        # Create other catalog items
        self._create_revistes(fake, fake_en, options['revistes'], llengues, paisos, categories, options['exemplars'])
        self._create_cds(fake, options['cds'], categories, options['exemplars'])
        self._create_dvds(fake, options['dvds'], categories, options['exemplars'])
        self._create_brs(fake, options['brs'], categories, options['exemplars'])
        self._create_dispositius(fake, options['dispositius'], categories, options['exemplars'])
        
        # Create users
        self._create_users(fake, options['usuaris'])

        # Create loans and reservations
        self._create_prestecs(fake, options['prestecs'])
        self._create_reservas(fake, options['reservas'])

        self.stdout.write(self.style.SUCCESS('Successfully seeded database'))

    def _setup_initial_data(self, fake):
        # Create languages if none exist
        if Llengua.objects.count() == 0:
            llengues = [
                Llengua.objects.create(nom="Català"),
                Llengua.objects.create(nom="Castellà"),
                Llengua.objects.create(nom="Anglès"),
                Llengua.objects.create(nom="Francès"),
                Llengua.objects.create(nom="Alemany")
            ]
        else:
            llengues = list(Llengua.objects.all())
        
        # Create countries if none exist
        if Pais.objects.count() == 0:
            paisos = [
                Pais.objects.create(nom="Catalunya"),
                Pais.objects.create(nom="Espanya"),
                Pais.objects.create(nom="Estats Units"),
                Pais.objects.create(nom="Regne Unit"),
                Pais.objects.create(nom="França"),
                Pais.objects.create(nom="Alemanya"),
                Pais.objects.create(nom="Itàlia")
            ]
        else:
            paisos = list(Pais.objects.all())
        
        # Create categories if none exist
        if Categoria.objects.count() == 0:
            # Main categories
            literatura = Categoria.objects.create(nom="Literatura")
            ciencia = Categoria.objects.create(nom="Ciència")
            tecnologia = Categoria.objects.create(nom="Tecnologia")
            historia = Categoria.objects.create(nom="Història")
            art = Categoria.objects.create(nom="Art")
            musica = Categoria.objects.create(nom="Música")
            cinema = Categoria.objects.create(nom="Cinema")
            informatica = Categoria.objects.create(nom="Informàtica")
            
            # Subcategories
            Categoria.objects.create(nom="Novel·la", parent=literatura)
            Categoria.objects.create(nom="Poesia", parent=literatura)
            Categoria.objects.create(nom="Teatre", parent=literatura)
            Categoria.objects.create(nom="Física", parent=ciencia)
            Categoria.objects.create(nom="Química", parent=ciencia)
            Categoria.objects.create(nom="Biologia", parent=ciencia)
            Categoria.objects.create(nom="Programació", parent=informatica)
            Categoria.objects.create(nom="Xarxes", parent=informatica)
            Categoria.objects.create(nom="Seguretat", parent=informatica)
            Categoria.objects.create(nom="Rock", parent=musica)
            Categoria.objects.create(nom="Clàssica", parent=musica)
            Categoria.objects.create(nom="Jazz", parent=musica)
            Categoria.objects.create(nom="Drama", parent=cinema)
            Categoria.objects.create(nom="Comèdia", parent=cinema)
            Categoria.objects.create(nom="Acció", parent=cinema)
        
        categories = list(Categoria.objects.all())
        return llengues, paisos, categories

    def _delete_existing_data(self):
        """Delete all existing data before seeding"""
        self.stdout.write("Deleting existing data...")
        # Delete related models first to avoid integrity errors
        Prestec.objects.all().delete()
        Reserva.objects.all().delete()
        Exemplar.objects.all().delete()
        Dispositiu.objects.all().delete()
        BR.objects.all().delete()
        DVD.objects.all().delete()
        CD.objects.all().delete()
        Revista.objects.all().delete()
        Llibre.objects.all().delete()
        # Also delete users except superusers
        Usuari.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS("All existing data deleted"))

    def _create_autors(self, fake, count):
        autors = []
        for _ in range(count):
            autor = {
                'nom': fake.name(),
                'nacionalitat': fake.country(),
                'data_naixement': fake.date_of_birth(minimum_age=20, maximum_age=100)
            }
            autors.append(autor)
        return autors

    def _create_llibres_for_autor(self, fake, fake_en, autor, num_llibres, llengues, paisos, categories, exemplars_count):
        with tqdm(total=num_llibres, desc=f"Creating books for author {autor['nom']}") as pbar:
            for _ in range(num_llibres):
                data_edicio = fake.date_between(
                    start_date='-70y',
                    end_date='today'
                )
                
                titol = fake.catch_phrase()
                titol_original = fake_en.catch_phrase() if random.random() > 0.7 else None
                
                # Create a book with complete data
                llibre = Llibre.objects.create(
                    titol=titol,
                    titol_original=titol_original,
                    autor=autor['nom'],
                    CDU=f"{random.randint(0, 9)}{random.randint(0, 99):02d}",
                    signatura=f"L-{random.randint(100, 999)}",
                    data_edicio=data_edicio,
                    resum=fake.paragraph(nb_sentences=5),
                    anotacions=fake.paragraph(nb_sentences=2) if random.random() > 0.7 else None,
                    mides=f"{random.randint(15, 30)} x {random.randint(10, 25)} cm",
                    ISBN=f"978{random.randint(1000000000, 9999999999)}",
                    editorial=fake.company(),
                    colleccio=fake.word().capitalize() + " " + fake.word() if random.random() > 0.6 else None,
                    lloc=fake.city(),
                    pais=random.choice(paisos),
                    llengua=random.choice(llengues),
                    pagines=random.randint(50, 800)
                )
                
                # Add random categories (2-3)
                for _ in range(random.randint(2, 3)):
                    llibre.tags.add(random.choice(categories))
                
                # Ensure 4-6 exemplars per book
                real_exemplars = random.randint(4, 6)
                self._create_exemplars(llibre, real_exemplars)
                pbar.update(1)

    def _create_revistes(self, fake, fake_en, count, llengues, paisos, categories, exemplars_count):
        with tqdm(total=count, desc="Creating magazines") as pbar:
            editorials = [fake.company() for _ in range(20)]  # Create a pool of publishers
            
            for _ in range(count):
                data_edicio = fake.date_between(start_date='-40y', end_date='today')
                editorial = random.choice(editorials)
                
                revista = Revista.objects.create(
                    titol=fake.catch_phrase(),
                    titol_original=fake_en.catch_phrase() if random.random() > 0.8 else None,
                    autor=fake.name() if random.random() > 0.1 else None,
                    CDU=f"{random.randint(0, 9)}{random.randint(0, 99):02d}",
                    signatura=f"R-{random.randint(100, 999)}",
                    data_edicio=data_edicio,
                    resum=fake.paragraph(nb_sentences=3),
                    anotacions=fake.paragraph(nb_sentences=1) if random.random() > 0.8 else None,
                    mides=f"{random.randint(15, 30)} x {random.randint(10, 25)} cm",
                    ISSN=f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                    editorial=editorial,
                    lloc=fake.city(),
                    pais=random.choice(paisos),
                    llengua=random.choice(llengues),
                    numero=random.randint(1, 100),
                    pagines=random.randint(20, 150)
                )
                
                # Add categories (2-3)
                for _ in range(random.randint(2, 3)):
                    revista.tags.add(random.choice(categories))
                
                # Create exemplars
                self._create_exemplars(revista, random.randint(1, exemplars_count))
                pbar.update(1)

    def _create_cds(self, fake, count, categories, exemplars_count):
        with tqdm(total=count, desc="Creating CDs") as pbar:
            music_styles = ["Rock", "Pop", "Jazz", "Clàssica", "Electrònica", "Hip-Hop", "Folk", "Blues", "Metal", "Indie"]
            record_labels = ["Sony Music", "Universal Music", "Warner Music", "EMI", "Columbia Records", "Capitol Records", 
                            "Atlantic Records", "Merge Records", "Sub Pop", "Matador Records"]
            
            for _ in range(count):
                # Create random duration between 30min and 75min - FIXED to handle durations > 60 minutes
                total_minutes = random.randint(30, 75)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                seconds = random.randint(0, 59)
                
                # Now both hours and minutes are in valid ranges
                duration = time(hour=hours, minute=minutes, second=seconds)
                
                # Create a CD
                cd = CD.objects.create(
                    titol=fake.sentence(nb_words=3)[:-1],  # Album title
                    titol_original=fake.sentence(nb_words=3)[:-1] if random.random() > 0.8 else None,
                    autor=fake.name() if random.random() > 0.1 else None,  # Artist name
                    CDU=f"{random.randint(0, 9)}{random.randint(0, 99):02d}",
                    signatura=f"CD-{random.randint(100, 999)}",
                    data_edicio=fake.date_between(start_date='-30y', end_date='today'),
                    resum=fake.paragraph(nb_sentences=2) if random.random() > 0.6 else None,
                    anotacions=fake.paragraph(nb_sentences=1) if random.random() > 0.8 else None,
                    mides="12 cm" if random.random() > 0.5 else None,  # Standard CD size
                    # CD specific fields
                    discografica=random.choice(record_labels),
                    estil=random.choice(music_styles),
                    duracio=duration
                )
                
                # Add random categories (1-2)
                music_category = next((c for c in categories if c.nom == "Música"), None)
                if music_category:
                    cd.tags.add(music_category)
                    
                    # Try to add a music subcategory if available
                    music_subcategories = [c for c in categories if c.parent and c.parent.nom == "Música"]
                    if music_subcategories and random.random() > 0.5:
                        cd.tags.add(random.choice(music_subcategories))
                else:
                    # Fallback to random categories
                    for _ in range(random.randint(1, 2)):
                        cd.tags.add(random.choice(categories))
                
                # Create exemplars for the CD
                self._create_exemplars(cd, exemplars_count)
                pbar.update(1)
            
            self.stdout.write(f"Created {count} CDs")

    def _create_dvds(self, fake, count, categories, exemplars_count):
        with tqdm(total=count, desc="Creating DVDs") as pbar:
            production_companies = ["Universal Pictures", "Warner Bros.", "20th Century Studios", "Paramount Pictures", 
                                "Sony Pictures", "Walt Disney Pictures", "Metro-Goldwyn-Mayer", "DreamWorks", 
                                "Focus Features", "A24"]
            
            for _ in range(count):
                # Create random duration between 1h and 3h59m
                hours = random.randint(1, 3)
                minutes = random.randint(0, 59)
                seconds = 0
                
                duration = time(hour=hours, minute=minutes, second=seconds)
                
                # Create a DVD
                dvd = DVD.objects.create(
                    titol=fake.sentence(nb_words=4)[:-1],  # Movie title
                    titol_original=fake.sentence(nb_words=4)[:-1] if random.random() > 0.6 else None,
                    autor=fake.name() if random.random() > 0.1 else None,  # Director
                    CDU=f"{random.randint(0, 9)}{random.randint(0, 99):02d}",
                    signatura=f"DVD-{random.randint(100, 999)}",
                    data_edicio=fake.date_between(start_date='-25y', end_date='today'),
                    resum=fake.paragraph(nb_sentences=3) if random.random() > 0.4 else None,
                    anotacions=fake.paragraph(nb_sentences=1) if random.random() > 0.7 else None,
                    mides="12 cm" if random.random() > 0.5 else None,  # Standard DVD size
                    # DVD specific fields
                    productora=random.choice(production_companies),
                    duracio=duration
                )
                
                # Add random categories (1-2)
                cinema_category = next((c for c in categories if c.nom == "Cinema"), None)
                if cinema_category:
                    dvd.tags.add(cinema_category)
                    
                    # Try to add a cinema subcategory if available
                    cinema_subcategories = [c for c in categories if c.parent and c.parent.nom == "Cinema"]
                    if cinema_subcategories and random.random() > 0.5:
                        dvd.tags.add(random.choice(cinema_subcategories))
                else:
                    # Fallback to random categories
                    for _ in range(random.randint(1, 2)):
                        dvd.tags.add(random.choice(categories))
                
                # Create exemplars for the DVD
                self._create_exemplars(dvd, exemplars_count)
                pbar.update(1)
            
            self.stdout.write(f"Created {count} DVDs")

    def _create_brs(self, fake, count, categories, exemplars_count):
        with tqdm(total=count, desc="Creating Blu-rays") as pbar:
            production_companies = ["Universal Pictures", "Warner Bros.", "20th Century Studios", "Paramount Pictures", 
                                "Sony Pictures", "Walt Disney Pictures", "Metro-Goldwyn-Mayer", "DreamWorks", 
                                "Focus Features", "A24"]
            
            for _ in range(count):
                # Create random duration between 1h30m and 3h30m (typical for Blu-rays)
                hours = random.randint(1, 3)
                minutes = random.randint(0, 59)
                seconds = 0
                
                duration = time(hour=hours, minute=minutes, second=seconds)
                
                # Create a Blu-ray
                br = BR.objects.create(
                    titol=fake.sentence(nb_words=4)[:-1],  # Movie title
                    titol_original=fake.sentence(nb_words=4)[:-1] if random.random() > 0.6 else None,
                    autor=fake.name() if random.random() > 0.1 else None,  # Director
                    CDU=f"{random.randint(0, 9)}{random.randint(0, 99):02d}",
                    signatura=f"BR-{random.randint(100, 999)}",
                    data_edicio=fake.date_between(start_date='-15y', end_date='today'),  # Blu-rays are newer
                    resum=fake.paragraph(nb_sentences=3) if random.random() > 0.4 else None,
                    anotacions=fake.paragraph(nb_sentences=1) if random.random() > 0.7 else None,
                    mides="12 cm" if random.random() > 0.5 else None,  # Standard Blu-ray size
                    # BR specific fields
                    productora=random.choice(production_companies),
                    duracio=duration
                )
                
                # Add random categories (1-2)
                cinema_category = next((c for c in categories if c.nom == "Cinema"), None)
                if cinema_category:
                    br.tags.add(cinema_category)
                    
                    # Try to add a cinema subcategory if available
                    cinema_subcategories = [c for c in categories if c.parent and c.parent.nom == "Cinema"]
                    if cinema_subcategories and random.random() > 0.5:
                        br.tags.add(random.choice(cinema_subcategories))
                else:
                    # Fallback to random categories
                    for _ in range(random.randint(1, 2)):
                        br.tags.add(random.choice(categories))
                
                # Create exemplars for the Blu-ray
                self._create_exemplars(br, exemplars_count)
                pbar.update(1)
            
            self.stdout.write(f"Created {count} Blu-rays")

    def _create_dispositius(self, fake, count, categories, exemplars_count):
        with tqdm(total=count, desc="Creating devices") as pbar:
            device_brands = ["Apple", "Samsung", "Sony", "Microsoft", "Lenovo", "Dell", "HP", "ASUS", "Acer", "Xiaomi"]
            device_types = ["Portàtil", "Tauleta", "Lector de llibres electrònics", "Càmera", "Reproductor MP3", 
                        "Auriculars", "Televisor", "Consola", "Ratolí", "Teclat"]
            
            for i in range(count):
                brand = random.choice(device_brands)
                device_type = random.choice(device_types)
                model = f"{brand} {device_type} {random.choice(['Pro', 'Lite', 'Plus', 'Max', 'Ultra', ''])}"
                
                # Create a device
                dispositiu = Dispositiu.objects.create(
                    titol=f"{brand} {device_type}",
                    titol_original=None,  # Devices typically don't have original titles
                    autor=None,  # Devices don't have authors
                    CDU=f"{random.randint(0, 9)}{random.randint(0, 99):02d}",
                    signatura=f"D-{random.randint(100, 999)}",
                    data_edicio=fake.date_between(start_date='-10y', end_date='today'),  # Modern devices
                    resum=fake.paragraph(nb_sentences=2) if random.random() > 0.5 else None,
                    anotacions=fake.paragraph(nb_sentences=1) if random.random() > 0.7 else None,
                    mides=f"{random.randint(10, 40)} x {random.randint(5, 30)} x {random.randint(1, 5)} cm" if random.random() > 0.3 else None,
                    # Dispositiu specific fields
                    marca=brand,
                    model=model if random.random() > 0.1 else None
                )
                
                # Add random categories (1-2)
                tech_category = next((c for c in categories if c.nom == "Tecnologia"), None)
                if tech_category:
                    dispositiu.tags.add(tech_category)
                    
                    # Try to add an informatics subcategory if available and relevant
                    if device_type in ["Portàtil", "Tauleta"]:
                        info_category = next((c for c in categories if c.nom == "Informàtica"), None)
                        if info_category:
                            dispositiu.tags.add(info_category)
                else:
                    # Fallback to random categories
                    for _ in range(random.randint(1, 2)):
                        dispositiu.tags.add(random.choice(categories))
                
                # Create exemplars for the device
                self._create_exemplars(dispositiu, exemplars_count)
                pbar.update(1)
            
            self.stdout.write(f"Created {count} devices")

    def _create_exemplars(self, cataleg_item, count):
        """Create a specific number of exemplars (copies) for a catalog item"""
        for i in range(count):
            # Some random variation in exemplar status
            exclos_prestec = random.random() < 0.2  # 20% excluded from loans
            baixa = random.random() < 0.1  # 10% out of circulation
            
            Exemplar.objects.create(
                cataleg=cataleg_item,
                registre=f"{cataleg_item.signatura}-{i+1}",
                exclos_prestec=exclos_prestec,
                baixa=baixa
            )

    def _create_users(self, fake, count):
        with tqdm(total=count, desc="Creating users") as pbar:
            centres = Centre.objects.all()
            cicles = Cicle.objects.all()
            
            for _ in range(count):
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = fake.email()
                username = f"{first_name[0].lower()}{last_name.lower()}{random.randint(1,99)}"
                
                user = Usuari.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                    centre=random.choice(centres) if centres else None,
                    cicle=random.choice(cicles) if cicles else None,
                    telefon=f"6{random.randint(10000000, 99999999)}"
                )
                user.set_password('password123')  # Set a default password
                user.save()
                pbar.update(1)

    def _create_prestecs(self, fake, count):
        """Create random loans"""
        self.stdout.write("Creating loans...")
        users = list(Usuari.objects.all())
        available_exemplars = list(Exemplar.objects.filter(exclos_prestec=False, baixa=False))

        if not users or not available_exemplars:
            self.stdout.write(self.style.WARNING('No users or available exemplars for loans'))
            return

        with tqdm(total=count, desc="Creating loans") as pbar:
            for _ in range(count):
                user = random.choice(users)
                exemplar = random.choice(available_exemplars)
                
                # Random date in the last 6 months
                start_date = fake.date_between(start_date='-6m', end_date='today')
                
                # 70% chance of being returned
                if random.random() < 0.7:
                    end_date = fake.date_between(start_date=start_date, end_date='today')
                else:
                    end_date = None

                Prestec.objects.create(
                    usuari=user,
                    exemplar=exemplar,
                    data_prestec=start_date,
                    data_retorn=end_date,
                    anotacions=fake.text(max_nb_chars=100) if random.random() > 0.8 else None
                )
                pbar.update(1)

    def _create_reservas(self, fake, count):
        """Create random reservations"""
        self.stdout.write("Creating reservations...")
        users = list(Usuari.objects.all())
        exemplars = list(Exemplar.objects.filter(exclos_prestec=False, baixa=False))

        if not users or not exemplars:
            self.stdout.write(self.style.WARNING('No users or exemplars for reservations'))
            return

        with tqdm(total=count, desc="Creating reservations") as pbar:
            for _ in range(count):
                user = random.choice(users)
                exemplar = random.choice(exemplars)
                
                Reserva.objects.create(
                    usuari=user,
                    exemplar=exemplar,
                    data=fake.date_between(start_date='-1m', end_date='today')
                )
                pbar.update(1)