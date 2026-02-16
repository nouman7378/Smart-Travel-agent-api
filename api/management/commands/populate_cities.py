"""
Management command to populate the City database with major airports.
Run with: python manage.py populate_cities
"""
from django.core.management.base import BaseCommand
from api.models import City


class Command(BaseCommand):
    help = 'Populate the database with major cities and airports'

    def handle(self, *args, **options):
        # Major international airports data
        airports = [
            # Pakistan
            {'name': 'Karachi', 'iata_code': 'KHI', 'airport_name': 'Jinnah International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Lahore', 'iata_code': 'LHE', 'airport_name': 'Allama Iqbal International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Islamabad', 'iata_code': 'ISB', 'airport_name': 'Islamabad International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Peshawar', 'iata_code': 'PEW', 'airport_name': 'Bacha Khan International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Quetta', 'iata_code': 'UET', 'airport_name': 'Quetta International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Multan', 'iata_code': 'MUX', 'airport_name': 'Multan International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Faisalabad', 'iata_code': 'LYP', 'airport_name': 'Faisalabad International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            {'name': 'Sialkot', 'iata_code': 'SKT', 'airport_name': 'Sialkot International Airport', 'country': 'Pakistan', 'country_code': 'PK', 'timezone': 'Asia/Karachi'},
            
            # United Arab Emirates
            {'name': 'Dubai', 'iata_code': 'DXB', 'airport_name': 'Dubai International Airport', 'country': 'United Arab Emirates', 'country_code': 'AE', 'timezone': 'Asia/Dubai'},
            {'name': 'Abu Dhabi', 'iata_code': 'AUH', 'airport_name': 'Zayed International Airport', 'country': 'United Arab Emirates', 'country_code': 'AE', 'timezone': 'Asia/Dubai'},
            {'name': 'Sharjah', 'iata_code': 'SHJ', 'airport_name': 'Sharjah International Airport', 'country': 'United Arab Emirates', 'country_code': 'AE', 'timezone': 'Asia/Dubai'},
            
            # Saudi Arabia
            {'name': 'Jeddah', 'iata_code': 'JED', 'airport_name': 'King Abdulaziz International Airport', 'country': 'Saudi Arabia', 'country_code': 'SA', 'timezone': 'Asia/Riyadh'},
            {'name': 'Riyadh', 'iata_code': 'RUH', 'airport_name': 'King Khalid International Airport', 'country': 'Saudi Arabia', 'country_code': 'SA', 'timezone': 'Asia/Riyadh'},
            {'name': 'Dammam', 'iata_code': 'DMM', 'airport_name': 'King Fahd International Airport', 'country': 'Saudi Arabia', 'country_code': 'SA', 'timezone': 'Asia/Riyadh'},
            {'name': 'Medina', 'iata_code': 'MED', 'airport_name': 'Prince Mohammad bin Abdulaziz Airport', 'country': 'Saudi Arabia', 'country_code': 'SA', 'timezone': 'Asia/Riyadh'},
            
            # Qatar
            {'name': 'Doha', 'iata_code': 'DOH', 'airport_name': 'Hamad International Airport', 'country': 'Qatar', 'country_code': 'QA', 'timezone': 'Asia/Qatar'},
            
            # Turkey
            {'name': 'Istanbul', 'iata_code': 'IST', 'airport_name': 'Istanbul Airport', 'country': 'Turkey', 'country_code': 'TR', 'timezone': 'Europe/Istanbul'},
            {'name': 'Ankara', 'iata_code': 'ESB', 'airport_name': 'Ankara Esenboga Airport', 'country': 'Turkey', 'country_code': 'TR', 'timezone': 'Europe/Istanbul'},
            {'name': 'Antalya', 'iata_code': 'AYT', 'airport_name': 'Antalya Airport', 'country': 'Turkey', 'country_code': 'TR', 'timezone': 'Europe/Istanbul'},
            
            # Europe - Major hubs
            {'name': 'London', 'iata_code': 'LHR', 'airport_name': 'Heathrow Airport', 'country': 'United Kingdom', 'country_code': 'GB', 'timezone': 'Europe/London'},
            {'name': 'London', 'iata_code': 'LGW', 'airport_name': 'Gatwick Airport', 'country': 'United Kingdom', 'country_code': 'GB', 'timezone': 'Europe/London'},
            {'name': 'Paris', 'iata_code': 'CDG', 'airport_name': 'Charles de Gaulle Airport', 'country': 'France', 'country_code': 'FR', 'timezone': 'Europe/Paris'},
            {'name': 'Paris', 'iata_code': 'ORY', 'airport_name': 'Orly Airport', 'country': 'France', 'country_code': 'FR', 'timezone': 'Europe/Paris'},
            {'name': 'Frankfurt', 'iata_code': 'FRA', 'airport_name': 'Frankfurt Airport', 'country': 'Germany', 'country_code': 'DE', 'timezone': 'Europe/Berlin'},
            {'name': 'Munich', 'iata_code': 'MUC', 'airport_name': 'Munich Airport', 'country': 'Germany', 'country_code': 'DE', 'timezone': 'Europe/Berlin'},
            {'name': 'Berlin', 'iata_code': 'BER', 'airport_name': 'Berlin Brandenburg Airport', 'country': 'Germany', 'country_code': 'DE', 'timezone': 'Europe/Berlin'},
            {'name': 'Amsterdam', 'iata_code': 'AMS', 'airport_name': 'Amsterdam Airport Schiphol', 'country': 'Netherlands', 'country_code': 'NL', 'timezone': 'Europe/Amsterdam'},
            {'name': 'Rome', 'iata_code': 'FCO', 'airport_name': 'Leonardo da Vinci International Airport', 'country': 'Italy', 'country_code': 'IT', 'timezone': 'Europe/Rome'},
            {'name': 'Milan', 'iata_code': 'MXP', 'airport_name': 'Milan Malpensa Airport', 'country': 'Italy', 'country_code': 'IT', 'timezone': 'Europe/Rome'},
            {'name': 'Madrid', 'iata_code': 'MAD', 'airport_name': 'Adolfo Suarez Madrid-Barajas Airport', 'country': 'Spain', 'country_code': 'ES', 'timezone': 'Europe/Madrid'},
            {'name': 'Barcelona', 'iata_code': 'BCN', 'airport_name': 'Barcelona-El Prat Airport', 'country': 'Spain', 'country_code': 'ES', 'timezone': 'Europe/Madrid'},
            {'name': 'Zurich', 'iata_code': 'ZRH', 'airport_name': 'Zurich Airport', 'country': 'Switzerland', 'country_code': 'CH', 'timezone': 'Europe/Zurich'},
            {'name': 'Vienna', 'iata_code': 'VIE', 'airport_name': 'Vienna International Airport', 'country': 'Austria', 'country_code': 'AT', 'timezone': 'Europe/Vienna'},
            {'name': 'Brussels', 'iata_code': 'BRU', 'airport_name': 'Brussels Airport', 'country': 'Belgium', 'country_code': 'BE', 'timezone': 'Europe/Brussels'},
            {'name': 'Copenhagen', 'iata_code': 'CPH', 'airport_name': 'Copenhagen Airport', 'country': 'Denmark', 'country_code': 'DK', 'timezone': 'Europe/Copenhagen'},
            {'name': 'Stockholm', 'iata_code': 'ARN', 'airport_name': 'Stockholm Arlanda Airport', 'country': 'Sweden', 'country_code': 'SE', 'timezone': 'Europe/Stockholm'},
            {'name': 'Oslo', 'iata_code': 'OSL', 'airport_name': 'Oslo Airport', 'country': 'Norway', 'country_code': 'NO', 'timezone': 'Europe/Oslo'},
            {'name': 'Helsinki', 'iata_code': 'HEL', 'airport_name': 'Helsinki-Vantaa Airport', 'country': 'Finland', 'country_code': 'FI', 'timezone': 'Europe/Helsinki'},
            {'name': 'Athens', 'iata_code': 'ATH', 'airport_name': 'Athens International Airport', 'country': 'Greece', 'country_code': 'GR', 'timezone': 'Europe/Athens'},
            {'name': 'Lisbon', 'iata_code': 'LIS', 'airport_name': 'Lisbon Airport', 'country': 'Portugal', 'country_code': 'PT', 'timezone': 'Europe/Lisbon'},
            {'name': 'Dublin', 'iata_code': 'DUB', 'airport_name': 'Dublin Airport', 'country': 'Ireland', 'country_code': 'IE', 'timezone': 'Europe/Dublin'},
            {'name': 'Prague', 'iata_code': 'PRG', 'airport_name': 'Vaclav Havel Airport Prague', 'country': 'Czech Republic', 'country_code': 'CZ', 'timezone': 'Europe/Prague'},
            {'name': 'Warsaw', 'iata_code': 'WAW', 'airport_name': 'Warsaw Chopin Airport', 'country': 'Poland', 'country_code': 'PL', 'timezone': 'Europe/Warsaw'},
            {'name': 'Budapest', 'iata_code': 'BUD', 'airport_name': 'Budapest Ferenc Liszt International Airport', 'country': 'Hungary', 'country_code': 'HU', 'timezone': 'Europe/Budapest'},
            
            # North America
            {'name': 'New York', 'iata_code': 'JFK', 'airport_name': 'John F. Kennedy International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'New York', 'iata_code': 'LGA', 'airport_name': 'LaGuardia Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Newark', 'iata_code': 'EWR', 'airport_name': 'Newark Liberty International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Los Angeles', 'iata_code': 'LAX', 'airport_name': 'Los Angeles International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Los_Angeles'},
            {'name': 'Chicago', 'iata_code': 'ORD', 'airport_name': "O'Hare International Airport", 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Chicago'},
            {'name': 'San Francisco', 'iata_code': 'SFO', 'airport_name': 'San Francisco International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Los_Angeles'},
            {'name': 'Miami', 'iata_code': 'MIA', 'airport_name': 'Miami International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Boston', 'iata_code': 'BOS', 'airport_name': 'Logan International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Washington', 'iata_code': 'IAD', 'airport_name': 'Dulles International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Washington', 'iata_code': 'DCA', 'airport_name': 'Ronald Reagan Washington National Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Atlanta', 'iata_code': 'ATL', 'airport_name': 'Hartsfield-Jackson Atlanta International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Dallas', 'iata_code': 'DFW', 'airport_name': 'Dallas/Fort Worth International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Chicago'},
            {'name': 'Houston', 'iata_code': 'IAH', 'airport_name': 'George Bush Intercontinental Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Chicago'},
            {'name': 'Seattle', 'iata_code': 'SEA', 'airport_name': 'Seattle-Tacoma International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Los_Angeles'},
            {'name': 'Las Vegas', 'iata_code': 'LAS', 'airport_name': 'Harry Reid International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Los_Angeles'},
            {'name': 'Denver', 'iata_code': 'DEN', 'airport_name': 'Denver International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Denver'},
            {'name': 'Phoenix', 'iata_code': 'PHX', 'airport_name': 'Phoenix Sky Harbor International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Phoenix'},
            {'name': 'Philadelphia', 'iata_code': 'PHL', 'airport_name': 'Philadelphia International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Detroit', 'iata_code': 'DTW', 'airport_name': 'Detroit Metropolitan Wayne County Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/New_York'},
            {'name': 'Minneapolis', 'iata_code': 'MSP', 'airport_name': 'Minneapolis-Saint Paul International Airport', 'country': 'United States', 'country_code': 'US', 'timezone': 'America/Chicago'},
            {'name': 'Toronto', 'iata_code': 'YYZ', 'airport_name': 'Toronto Pearson International Airport', 'country': 'Canada', 'country_code': 'CA', 'timezone': 'America/Toronto'},
            {'name': 'Vancouver', 'iata_code': 'YVR', 'airport_name': 'Vancouver International Airport', 'country': 'Canada', 'country_code': 'CA', 'timezone': 'America/Vancouver'},
            {'name': 'Montreal', 'iata_code': 'YUL', 'airport_name': 'Montreal-Pierre Elliott Trudeau International Airport', 'country': 'Canada', 'country_code': 'CA', 'timezone': 'America/Toronto'},
            {'name': 'Calgary', 'iata_code': 'YYC', 'airport_name': 'Calgary International Airport', 'country': 'Canada', 'country_code': 'CA', 'timezone': 'America/Edmonton'},
            {'name': 'Mexico City', 'iata_code': 'MEX', 'airport_name': 'Mexico City International Airport', 'country': 'Mexico', 'country_code': 'MX', 'timezone': 'America/Mexico_City'},
            {'name': 'Cancun', 'iata_code': 'CUN', 'airport_name': 'Cancun International Airport', 'country': 'Mexico', 'country_code': 'MX', 'timezone': 'America/Cancun'},
            
            # Asia
            {'name': 'Tokyo', 'iata_code': 'NRT', 'airport_name': 'Narita International Airport', 'country': 'Japan', 'country_code': 'JP', 'timezone': 'Asia/Tokyo'},
            {'name': 'Tokyo', 'iata_code': 'HND', 'airport_name': 'Haneda Airport', 'country': 'Japan', 'country_code': 'JP', 'timezone': 'Asia/Tokyo'},
            {'name': 'Osaka', 'iata_code': 'KIX', 'airport_name': 'Kansai International Airport', 'country': 'Japan', 'country_code': 'JP', 'timezone': 'Asia/Tokyo'},
            {'name': 'Seoul', 'iata_code': 'ICN', 'airport_name': 'Incheon International Airport', 'country': 'South Korea', 'country_code': 'KR', 'timezone': 'Asia/Seoul'},
            {'name': 'Beijing', 'iata_code': 'PEK', 'airport_name': 'Beijing Capital International Airport', 'country': 'China', 'country_code': 'CN', 'timezone': 'Asia/Shanghai'},
            {'name': 'Beijing', 'iata_code': 'PKX', 'airport_name': 'Beijing Daxing International Airport', 'country': 'China', 'country_code': 'CN', 'timezone': 'Asia/Shanghai'},
            {'name': 'Shanghai', 'iata_code': 'PVG', 'airport_name': 'Shanghai Pudong International Airport', 'country': 'China', 'country_code': 'CN', 'timezone': 'Asia/Shanghai'},
            {'name': 'Hong Kong', 'iata_code': 'HKG', 'airport_name': 'Hong Kong International Airport', 'country': 'Hong Kong', 'country_code': 'HK', 'timezone': 'Asia/Hong_Kong'},
            {'name': 'Singapore', 'iata_code': 'SIN', 'airport_name': 'Singapore Changi Airport', 'country': 'Singapore', 'country_code': 'SG', 'timezone': 'Asia/Singapore'},
            {'name': 'Bangkok', 'iata_code': 'BKK', 'airport_name': 'Suvarnabhumi Airport', 'country': 'Thailand', 'country_code': 'TH', 'timezone': 'Asia/Bangkok'},
            {'name': 'Kuala Lumpur', 'iata_code': 'KUL', 'airport_name': 'Kuala Lumpur International Airport', 'country': 'Malaysia', 'country_code': 'MY', 'timezone': 'Asia/Kuala_Lumpur'},
            {'name': 'Jakarta', 'iata_code': 'CGK', 'airport_name': 'Soekarno-Hatta International Airport', 'country': 'Indonesia', 'country_code': 'ID', 'timezone': 'Asia/Jakarta'},
            {'name': 'Manila', 'iata_code': 'MNL', 'airport_name': 'Ninoy Aquino International Airport', 'country': 'Philippines', 'country_code': 'PH', 'timezone': 'Asia/Manila'},
            {'name': 'Mumbai', 'iata_code': 'BOM', 'airport_name': 'Chhatrapati Shivaji Maharaj International Airport', 'country': 'India', 'country_code': 'IN', 'timezone': 'Asia/Kolkata'},
            {'name': 'Delhi', 'iata_code': 'DEL', 'airport_name': 'Indira Gandhi International Airport', 'country': 'India', 'country_code': 'IN', 'timezone': 'Asia/Kolkata'},
            {'name': 'Bangalore', 'iata_code': 'BLR', 'airport_name': 'Kempegowda International Airport', 'country': 'India', 'country_code': 'IN', 'timezone': 'Asia/Kolkata'},
            {'name': 'Chennai', 'iata_code': 'MAA', 'airport_name': 'Chennai International Airport', 'country': 'India', 'country_code': 'IN', 'timezone': 'Asia/Kolkata'},
            {'name': 'Hyderabad', 'iata_code': 'HYD', 'airport_name': 'Rajiv Gandhi International Airport', 'country': 'India', 'country_code': 'IN', 'timezone': 'Asia/Kolkata'},
            {'name': 'Kolkata', 'iata_code': 'CCU', 'airport_name': 'Netaji Subhas Chandra Bose International Airport', 'country': 'India', 'country_code': 'IN', 'timezone': 'Asia/Kolkata'},
            
            # Australia & Oceania
            {'name': 'Sydney', 'iata_code': 'SYD', 'airport_name': 'Sydney Kingsford Smith Airport', 'country': 'Australia', 'country_code': 'AU', 'timezone': 'Australia/Sydney'},
            {'name': 'Melbourne', 'iata_code': 'MEL', 'airport_name': 'Melbourne Airport', 'country': 'Australia', 'country_code': 'AU', 'timezone': 'Australia/Melbourne'},
            {'name': 'Brisbane', 'iata_code': 'BNE', 'airport_name': 'Brisbane Airport', 'country': 'Australia', 'country_code': 'AU', 'timezone': 'Australia/Brisbane'},
            {'name': 'Perth', 'iata_code': 'PER', 'airport_name': 'Perth Airport', 'country': 'Australia', 'country_code': 'AU', 'timezone': 'Australia/Perth'},
            {'name': 'Auckland', 'iata_code': 'AKL', 'airport_name': 'Auckland Airport', 'country': 'New Zealand', 'country_code': 'NZ', 'timezone': 'Pacific/Auckland'},
            
            # Africa
            {'name': 'Cairo', 'iata_code': 'CAI', 'airport_name': 'Cairo International Airport', 'country': 'Egypt', 'country_code': 'EG', 'timezone': 'Africa/Cairo'},
            {'name': 'Cape Town', 'iata_code': 'CPT', 'airport_name': 'Cape Town International Airport', 'country': 'South Africa', 'country_code': 'ZA', 'timezone': 'Africa/Johannesburg'},
            {'name': 'Johannesburg', 'iata_code': 'JNB', 'airport_name': 'O.R. Tambo International Airport', 'country': 'South Africa', 'country_code': 'ZA', 'timezone': 'Africa/Johannesburg'},
            {'name': 'Casablanca', 'iata_code': 'CMN', 'airport_name': 'Mohammed V International Airport', 'country': 'Morocco', 'country_code': 'MA', 'timezone': 'Africa/Casablanca'},
            {'name': 'Nairobi', 'iata_code': 'NBO', 'airport_name': 'Jomo Kenyatta International Airport', 'country': 'Kenya', 'country_code': 'KE', 'timezone': 'Africa/Nairobi'},
            {'name': 'Addis Ababa', 'iata_code': 'ADD', 'airport_name': 'Addis Ababa Bole International Airport', 'country': 'Ethiopia', 'country_code': 'ET', 'timezone': 'Africa/Addis_Ababa'},
            
            # South America
            {'name': 'Sao Paulo', 'iata_code': 'GRU', 'airport_name': 'Sao Paulo/Guarulhos International Airport', 'country': 'Brazil', 'country_code': 'BR', 'timezone': 'America/Sao_Paulo'},
            {'name': 'Rio de Janeiro', 'iata_code': 'GIG', 'airport_name': 'Rio de Janeiro-Galeao International Airport', 'country': 'Brazil', 'country_code': 'BR', 'timezone': 'America/Sao_Paulo'},
            {'name': 'Buenos Aires', 'iata_code': 'EZE', 'airport_name': 'Ministro Pistarini International Airport', 'country': 'Argentina', 'country_code': 'AR', 'timezone': 'America/Argentina/Buenos_Aires'},
            {'name': 'Lima', 'iata_code': 'LIM', 'airport_name': 'Jorge Chavez International Airport', 'country': 'Peru', 'country_code': 'PE', 'timezone': 'America/Lima'},
            {'name': 'Santiago', 'iata_code': 'SCL', 'airport_name': 'Arturo Merino Benitez International Airport', 'country': 'Chile', 'country_code': 'CL', 'timezone': 'America/Santiago'},
            {'name': 'Bogota', 'iata_code': 'BOG', 'airport_name': 'El Dorado International Airport', 'country': 'Colombia', 'country_code': 'CO', 'timezone': 'America/Bogota'},
            
            # Other Middle East
            {'name': 'Kuwait City', 'iata_code': 'KWI', 'airport_name': 'Kuwait International Airport', 'country': 'Kuwait', 'country_code': 'KW', 'timezone': 'Asia/Kuwait'},
            {'name': 'Bahrain', 'iata_code': 'BAH', 'airport_name': 'Bahrain International Airport', 'country': 'Bahrain', 'country_code': 'BH', 'timezone': 'Asia/Bahrain'},
            {'name': 'Muscat', 'iata_code': 'MCT', 'airport_name': 'Muscat International Airport', 'country': 'Oman', 'country_code': 'OM', 'timezone': 'Asia/Muscat'},
            {'name': 'Tehran', 'iata_code': 'IKA', 'airport_name': 'Imam Khomeini International Airport', 'country': 'Iran', 'country_code': 'IR', 'timezone': 'Asia/Tehran'},
            {'name': 'Amman', 'iata_code': 'AMM', 'airport_name': 'Queen Alia International Airport', 'country': 'Jordan', 'country_code': 'JO', 'timezone': 'Asia/Amman'},
            {'name': 'Beirut', 'iata_code': 'BEY', 'airport_name': 'Beirut-Rafic Hariri International Airport', 'country': 'Lebanon', 'country_code': 'LB', 'timezone': 'Asia/Beirut'},
            {'name': 'Baghdad', 'iata_code': 'BGW', 'airport_name': 'Baghdad International Airport', 'country': 'Iraq', 'country_code': 'IQ', 'timezone': 'Asia/Baghdad'},
        ]

        created_count = 0
        updated_count = 0

        for airport_data in airports:
            city, created = City.objects.update_or_create(
                iata_code=airport_data['iata_code'],
                defaults={
                    'name': airport_data['name'],
                    'airport_name': airport_data['airport_name'],
                    'country': airport_data['country'],
                    'country_code': airport_data.get('country_code', ''),
                    'timezone': airport_data.get('timezone', ''),
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated cities database. '
                f'Created: {created_count}, Updated: {updated_count}, '
                f'Total: {created_count + updated_count}'
            )
        )