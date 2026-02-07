import requests
import base64
import math
from config import EASYPOSTCODES_API_KEY, EPC_API_KEY, EPC_EMAIL, TRANSPORTAPI_APP_ID, TRANSPORTAPI_APP_KEY


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula
    Returns distance in meters
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance


def fetch_location_data(postcode):
    """
    Fetch geographic/location data for the postcode using Postcodes.io API
    
    API: https://api.postcodes.io/postcodes/{postcode}
    
    Returns:
        dict: Location data or None if error
    """
    try:
        # Remove any spaces from postcode for the API call
        postcode_clean = postcode.replace(' ', '')
        url = f'https://api.postcodes.io/postcodes/{postcode_clean}'
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            
            return {
                'postcode': result.get('postcode', postcode),
                'latitude': result.get('latitude'),
                'longitude': result.get('longitude'),
                'region': result.get('region'),
                'country': result.get('country'),
                'parliamentary_constituency': result.get('parliamentary_constituency'),
                'admin_district': result.get('admin_district'),
                'parish': result.get('parish'),
                'status': 'success'
            }
        else:
            print(f"Postcodes.io API returned status code: {response.status_code}")
            return {
                'postcode': postcode,
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("Postcodes.io API timeout")
        return {
            'postcode': postcode,
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location data: {e}")
        return {
            'postcode': postcode,
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching location data: {e}")
        return {
            'postcode': postcode,
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_crime_data(latitude, longitude):
    """
    Fetch crime statistics using UK Police API
    
    API: https://data.police.uk/api/crimes-street/all-crime
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        dict: Crime statistics with status indicator
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for crime lookup'
            }
        
        # UK Police API endpoint
        url = 'https://data.police.uk/api/crimes-street/all-crime'
        params = {
            'lat': latitude,
            'lng': longitude
        }
        
        print(f"Fetching crime data for coordinates: {latitude}, {longitude}")
        
        # First, get available dates with longer timeout
        dates_url = 'https://data.police.uk/api/crimes-street-dates'
        dates_response = requests.get(dates_url, timeout=20)
        
        if dates_response.status_code != 200:
            print(f"Could not fetch available dates")
            return {
                'status': 'error',
                'error_message': 'Unable to fetch available crime dates'
            }
        
        available_dates = dates_response.json()
        # Get the first 3 dates (most recent)
        months_to_fetch = [d['date'] for d in available_dates[:3]]
        
        monthly_totals = []
        latest_month_crimes = None
        latest_month = None
        
        # Fetch crimes for each of the 3 months with retry logic
        for i, month in enumerate(months_to_fetch):
            params_with_date = {
                'lat': latitude,
                'lng': longitude,
                'date': month
            }
            
            # Retry up to 2 times if it fails
            for attempt in range(2):
                try:
                    print(f"Fetching crimes for {month} (attempt {attempt + 1})")
                    month_response = requests.get(url, params=params_with_date, timeout=20)
                    
                    if month_response.status_code == 200:
                        month_crimes = month_response.json()
                        crime_count = len(month_crimes)
                        monthly_totals.append({
                            'month': month,
                            'count': crime_count
                        })
                        print(f"Found {crime_count} crimes in {month}")
                        
                        # Save the latest month's crimes for breakdown
                        if i == 0:
                            latest_month_crimes = month_crimes
                            latest_month = month
                        break  # Success, move to next month
                    else:
                        print(f"Failed to fetch {month}: status {month_response.status_code}")
                        if attempt == 1:  # Last attempt
                            print(f"Skipping {month} after retries")
                        
                except requests.exceptions.Timeout:
                    print(f"Timeout fetching {month} on attempt {attempt + 1}")
                    if attempt == 1:  # Last attempt
                        print(f"Skipping {month} after timeout")
        
        if not monthly_totals or not latest_month_crimes:
            return {
                'monthly_totals': [],
                'crime_types': {},
                'period': 'No data available',
                'status': 'success'
            }
        
        # Count crimes by type for the LATEST month only
        crime_counts = {}
        
        for crime in latest_month_crimes:
            crime_type = crime.get('category', 'unknown')
            crime_type_readable = crime_type.replace('-', ' ').title()
            
            if crime_type_readable not in crime_counts:
                crime_counts[crime_type_readable] = 0
            crime_counts[crime_type_readable] += 1
        
        # Sort by count descending
        sorted_crimes = dict(sorted(crime_counts.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'monthly_totals': monthly_totals,  # List of {month, count}
            'crime_types': sorted_crimes,
            'period': latest_month,
            'status': 'success'
        }
            
    except requests.exceptions.Timeout:
        print("UK Police API timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out after retries'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching crime data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching crime data: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_train_station_data(latitude, longitude):
    """
    Fetch nearby train station information using TransportAPI
    
    API: https://transportapi.com/
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        dict: Train station data with status indicator
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for station lookup'
            }
        
        # TransportAPI endpoint for nearby stations
        url = 'https://transportapi.com/v3/uk/places.json'
        params = {
            'lat': latitude,
            'lon': longitude,
            'type': 'train_station',
            'app_id': TRANSPORTAPI_APP_ID,
            'app_key': TRANSPORTAPI_APP_KEY
        }
        
        print(f"Fetching train station data for coordinates: {latitude}, {longitude}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"TransportAPI response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            places = data.get('member', [])
            
            print(f"Found {len(places)} train stations")
            
            if not places:
                return {
                    'stations': [],
                    'status': 'success'
                }
            
            # Get the 3 nearest stations
            stations = []
            for place in places[:3]:
                station_info = {
                    'name': place.get('name', 'Unknown'),
                    'distance': place.get('distance', 0),
                    'station_code': place.get('station_code', 'N/A')
                }
                stations.append(station_info)
                print(f"Station: {station_info['name']}, Distance: {station_info['distance']}m")
            
            return {
                'stations': stations,
                'status': 'success'
            }
        elif response.status_code == 401:
            print("TransportAPI 401: Invalid API credentials")
            return {
                'status': 'error',
                'error_message': 'Invalid TransportAPI credentials'
            }
        elif response.status_code == 429:
            print("TransportAPI 429: Rate limit exceeded")
            return {
                'status': 'error',
                'error_message': 'Rate limit exceeded'
            }
        else:
            print(f"TransportAPI returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("TransportAPI timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching train station data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching train station data: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_bus_stop_data(latitude, longitude):
    """
    Fetch nearby bus stop information using TransportAPI
    
    API: https://transportapi.com/
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        dict: Bus stop data with status indicator
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for bus stop lookup'
            }
        
        # TransportAPI endpoint for nearby bus stops
        url = 'https://transportapi.com/v3/uk/places.json'
        params = {
            'lat': latitude,
            'lon': longitude,
            'type': 'bus_stop',
            'app_id': TRANSPORTAPI_APP_ID,
            'app_key': TRANSPORTAPI_APP_KEY
        }
        
        print(f"Fetching bus stop data for coordinates: {latitude}, {longitude}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"TransportAPI bus stops response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            places = data.get('member', [])
            
            print(f"Found {len(places)} bus stops")
            
            if not places:
                return {
                    'stops': [],
                    'status': 'success'
                }
            
            # Get the 3 nearest bus stops
            stops = []
            for place in places[:3]:
                stop_info = {
                    'name': place.get('name', 'Unknown'),
                    'distance': place.get('distance', 0),
                    'indicator': place.get('indicator', 'N/A')
                }
                stops.append(stop_info)
                print(f"Bus stop: {stop_info['name']}, Distance: {stop_info['distance']}m")
            
            return {
                'stops': stops,
                'status': 'success'
            }
        elif response.status_code == 401:
            print("TransportAPI 401: Invalid API credentials")
            return {
                'status': 'error',
                'error_message': 'Invalid TransportAPI credentials'
            }
        elif response.status_code == 429:
            print("TransportAPI 429: Rate limit exceeded")
            return {
                'status': 'error',
                'error_message': 'Rate limit exceeded'
            }
        else:
            print(f"TransportAPI returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("TransportAPI timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching bus stop data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching bus stop data: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_tube_station_data(latitude, longitude):
    """
    Fetch nearby London Underground stations using TransportAPI
    Only returns stations within 3 miles
    
    API: https://transportapi.com/
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        dict: Tube station data with status indicator
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for tube station lookup'
            }
        
        # TransportAPI endpoint for nearby tube stations
        url = 'https://transportapi.com/v3/uk/places.json'
        params = {
            'lat': latitude,
            'lon': longitude,
            'type': 'tube_station',
            'app_id': TRANSPORTAPI_APP_ID,
            'app_key': TRANSPORTAPI_APP_KEY
        }
        
        print(f"Fetching tube station data for coordinates: {latitude}, {longitude}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"TransportAPI tube stations response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            places = data.get('member', [])
            
            print(f"Found {len(places)} tube stations")
            
            # Filter stations within 3 miles (4828 meters)
            THREE_MILES_IN_METERS = 4828
            nearby_stations = [p for p in places if p.get('distance', float('inf')) <= THREE_MILES_IN_METERS]
            
            print(f"{len(nearby_stations)} stations within 3 miles")
            
            if not nearby_stations:
                return {
                    'stations': [],
                    'status': 'none_nearby'  # Special status for "not in London/no nearby stations"
                }
            
            # Get the 3 nearest tube stations
            stations = []
            for place in nearby_stations[:3]:
                station_info = {
                    'name': place.get('name', 'Unknown'),
                    'distance': place.get('distance', 0),
                    'station_code': place.get('station_code', 'N/A')
                }
                stations.append(station_info)
                print(f"Tube station: {station_info['name']}, Distance: {station_info['distance']}m")
            
            return {
                'stations': stations,
                'status': 'success'
            }
        elif response.status_code == 401:
            print("TransportAPI 401: Invalid API credentials")
            return {
                'status': 'error',
                'error_message': 'Invalid TransportAPI credentials'
            }
        elif response.status_code == 429:
            print("TransportAPI 429: Rate limit exceeded")
            return {
                'status': 'error',
                'error_message': 'Rate limit exceeded'
            }
        else:
            print(f"TransportAPI returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("TransportAPI timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tube station data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching tube station data: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_epc_data(postcode, address):
    """
    Fetch Energy Performance Certificate data including council tax band
    
    API: https://epc.opendatacommunities.org/api/v1/domestic/search
    
    Args:
        postcode (str): UK postcode
        address (str): Full address to match
    
    Returns:
        dict: EPC data with status indicator
    """
    try:
        if EPC_API_KEY == 'your-epc-api-key-here':
            return {
                'status': 'error',
                'error_message': 'EPC API key not configured'
            }
        
        # EPC API endpoint
        url = 'https://epc.opendatacommunities.org/api/v1/domestic/search'
        
        # Format postcode - remove spaces
        postcode_clean = postcode.replace(' ', '')
        
        # Base64 encode email:api_key for Basic authentication
        auth_string = f'{EPC_EMAIL}:{EPC_API_KEY}'
        auth_bytes = auth_string.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode('ascii')
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {base64_auth}'
        }
        params = {
            'postcode': postcode_clean
        }
        
        print(f"=== EPC API DEBUG ===")
        print(f"Fetching EPC data for postcode: {postcode_clean}")
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        print(f"EPC Response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            print(f"Found {len(rows)} EPC records")
            
            if not rows:
                return {
                    'status': 'error',
                    'error_message': 'No EPC data found for this postcode'
                }
            
            # Try to match the address
            matched_record = None
            
            # Extract the house number/name from the selected address
            address_parts = [p.strip() for p in address.split(',')]
            first_part = address_parts[0] if address_parts else ""
            
            print(f"=== ADDRESS MATCHING ===")
            print(f"User selected address: {address}")
            print(f"First part to match: '{first_part}'")
            
            for i, row in enumerate(rows):
                epc_address = row.get('address', '')
                epc_address1 = row.get('address1', '')
                
                # Normalize addresses by removing commas and extra spaces for comparison
                first_part_normalized = first_part.replace(',', '').strip()
                epc_address_normalized = epc_address.replace(',', '').strip()
                epc_address1_normalized = epc_address1.replace(',', '').strip()
                
                # Check if the first part matches (case-insensitive)
                if first_part_normalized and (
                    first_part_normalized.lower() in epc_address_normalized.lower() or
                    first_part_normalized.lower() in epc_address1_normalized.lower()
                ):
                    matched_record = row
                    print(f"  *** MATCH FOUND! Using record {i+1} ***")
                    break
            
            # If no match, return error instead of using first record
            if not matched_record:
                print("\n=== NO MATCH FOUND ===")
                return {
                    'status': 'error',
                    'error_message': 'No EPC data found for this specific property'
                }
            
            return {
                'energy_rating': matched_record.get('current-energy-rating'),
                'potential_energy_rating': matched_record.get('potential-energy-rating'),
                'property_type': matched_record.get('property-type'),
                'built_form': matched_record.get('built-form'),
                'construction_age_band': matched_record.get('construction-age-band'),
                'total_floor_area': matched_record.get('total-floor-area'),
                'inspection_date': matched_record.get('inspection-date'),
                'matched_address': matched_record.get('address', 'Unknown'),
                'status': 'success'
            }
        elif response.status_code == 404:
            print("EPC 404: No data found")
            return {
                'status': 'error',
                'error_message': 'No EPC data found for this postcode'
            }
        elif response.status_code == 401:
            print("EPC 401: Unauthorized - Invalid API key")
            return {
                'status': 'error',
                'error_message': 'Invalid EPC API key'
            }
        else:
            print(f"EPC API returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("EPC API timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching EPC data: {e}")
        return {
            'status': 'error',
            'error_message': f'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching EPC data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': f'An unexpected error occurred'
        }


def fetch_tram_stop_data(latitude, longitude):
    """
    Fetch nearby tram/light rail stops using TransportAPI
    Only returns stops within 3 miles
    
    API: https://transportapi.com/
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        dict: Tram stop data with status indicator
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for tram stop lookup'
            }
        
        # TransportAPI endpoint for nearby tram stops
        url = 'https://transportapi.com/v3/uk/places.json'
        params = {
            'lat': latitude,
            'lon': longitude,
            'type': 'tram_stop',
            'app_id': TRANSPORTAPI_APP_ID,
            'app_key': TRANSPORTAPI_APP_KEY
        }
        
        print(f"Fetching tram stop data for coordinates: {latitude}, {longitude}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"TransportAPI tram stops response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            places = data.get('member', [])
            
            print(f"Found {len(places)} tram stops")
            
            # Filter stops within 3 miles (4828 meters)
            THREE_MILES_IN_METERS = 4828
            nearby_stops = [p for p in places if p.get('distance', float('inf')) <= THREE_MILES_IN_METERS]
            
            print(f"{len(nearby_stops)} tram stops within 3 miles")
            
            if not nearby_stops:
                return {
                    'stops': [],
                    'status': 'none_nearby'  # No tram system in this area or none within 3 miles
                }
            
            # Get the 3 nearest tram stops
            stops = []
            for place in nearby_stops[:3]:
                stop_info = {
                    'name': place.get('name', 'Unknown'),
                    'distance': place.get('distance', 0),
                    'indicator': place.get('indicator', 'N/A')
                }
                stops.append(stop_info)
                print(f"Tram stop: {stop_info['name']}, Distance: {stop_info['distance']}m")
            
            return {
                'stops': stops,
                'status': 'success'
            }
        elif response.status_code == 401:
            print("TransportAPI 401: Invalid API credentials")
            return {
                'status': 'error',
                'error_message': 'Invalid TransportAPI credentials'
            }
        elif response.status_code == 429:
            print("TransportAPI 429: Rate limit exceeded")
            return {
                'status': 'error',
                'error_message': 'Rate limit exceeded'
            }
        else:
            print(f"TransportAPI returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("TransportAPI timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tram stop data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching tram stop data: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_nearest_station_info(latitude, longitude, admin_district):
    """
    Fetch information about the nearest train station to the property
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
        admin_district (str): The administrative district/city name
    
    Returns:
        dict: Nearest station information
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available'
            }
        
        # Major UK city centers - used to determine typical destination
        city_centers = {
            'Westminster': 'Central London',
            'City of London': 'Central London',
            'Camden': 'Central London',
            'Islington': 'Central London',
            'Hackney': 'Central London',
            'Tower Hamlets': 'Central London',
            'Southwark': 'Central London',
            'Lambeth': 'Central London',
            'Birmingham': 'Birmingham City Centre',
            'Manchester': 'Manchester City Centre',
            'Leeds': 'Leeds City Centre',
            'Liverpool': 'Liverpool City Centre',
            'Newcastle upon Tyne': 'Newcastle City Centre',
            'Sheffield': 'Sheffield City Centre',
            'Bristol': 'Bristol City Centre',
            'Edinburgh': 'Edinburgh City Centre',
            'Glasgow': 'Glasgow City Centre',
            'Cardiff': 'Cardiff City Centre',
            'Nottingham': 'Nottingham City Centre',
            'Leicester': 'Leicester City Centre',
            'Coventry': 'Coventry City Centre',
        }
        
        # Find nearest train station to the property
        train_url = 'https://transportapi.com/v3/uk/places.json'
        train_params = {
            'lat': latitude,
            'lon': longitude,
            'type': 'train_station',
            'app_id': TRANSPORTAPI_APP_ID,
            'app_key': TRANSPORTAPI_APP_KEY
        }
        
        print(f"Finding nearest station near {admin_district}")
        
        train_response = requests.get(train_url, params=train_params, timeout=10)
        
        if train_response.status_code != 200:
            return {
                'status': 'error',
                'error_message': 'Could not find nearby stations'
            }
        
        train_data = train_response.json()
        stations = train_data.get('member', [])
        
        if not stations:
            return {
                'status': 'error',
                'error_message': 'No train stations found nearby'
            }
        
        # Get the nearest station
        nearest_station = stations[0]
        
        # Determine likely destination based on admin district
        destination = None
        for city, center_name in city_centers.items():
            if city.lower() in admin_district.lower():
                destination = center_name
                break
        
        # If not in a major city, default to Central London
        if not destination:
            destination = 'Central London'
        
        return {
            'station_name': nearest_station.get('name', 'Unknown'),
            'station_code': nearest_station.get('station_code', 'N/A'),
            'distance_miles': round(nearest_station.get('distance', 0) * 0.000621371, 2),
            'distance_meters': nearest_station.get('distance', 0),
            'typical_destination': destination,
            'status': 'success'
        }
        
    except requests.exceptions.Timeout:
        print("Station lookup timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching station info: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error fetching station info: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_schools_data(latitude, longitude):
    """
    Fetch nearby schools using OpenStreetMap Overpass API
    Returns primary and secondary schools within 15 miles
    
    API: https://overpass-api.de/
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
    
    Returns:
        dict: Schools data with primary and secondary schools
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for school lookup'
            }
        
        print(f"Fetching schools data for coordinates: {latitude}, {longitude}")
        
        # Convert 5 miles to meters for the radius search (REDUCED from 15)
        FIVE_MILES_IN_METERS = 8047
        
        # Overpass API endpoint
        url = 'https://overpass-api.de/api/interpreter'
        
        # Overpass QL query to find schools within 15 miles
        # We'll search for nodes and ways tagged as schools
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="school"](around:{FIFTEEN_MILES_IN_METERS},{latitude},{longitude});
          way["amenity"="school"](around:{FIFTEEN_MILES_IN_METERS},{latitude},{longitude});
        );
        out center;
        """
        
        print(f"Querying Overpass API with {FIFTEEN_MILES_IN_METERS}m radius")
        
        # RETRY LOGIC: Try up to 2 times (REDUCED from 4)
        for attempt in range(2):
            try:
                response = requests.post(url, data={'data': query}, timeout=30)
                
                print(f"Overpass API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get('elements', [])
                    
                    print(f"Found {len(elements)} schools in total")
                    
                    if not elements:
                        return {
                            'schools': [],
                            'status': 'success'
                        }
                    
                    # Process schools
                    all_schools = []
                    
                    for element in elements:
                        tags = element.get('tags', {})
                        name = tags.get('name', 'Unnamed School')
                        
                        # Get coordinates (for ways, use center)
                        if element.get('type') == 'node':
                            school_lat = element.get('lat')
                            school_lon = element.get('lon')
                        elif element.get('type') == 'way' and 'center' in element:
                            school_lat = element['center'].get('lat')
                            school_lon = element['center'].get('lon')
                        else:
                            continue  # Skip if no coordinates
                        
                        # Calculate distance
                        distance_meters = calculate_distance(latitude, longitude, school_lat, school_lon)
                        distance_miles = round(distance_meters * 0.000621371, 2)
                        
                        # Only include if within 5 miles (double-check)
                        if distance_miles > 5:
                            continue
                        
                        school_info = {
                            'name': name,
                            'distance_miles': distance_miles,
                            'distance_meters': int(distance_meters),
                            'address': tags.get('addr:street', 'Address not available'),
                            'town': tags.get('addr:city', tags.get('addr:town', tags.get('addr:village', 'N/A')))
                        }
                        
                        all_schools.append(school_info)
                    
                    # Sort by distance and take top 10
                    all_schools.sort(key=lambda x: x['distance_miles'])
                    all_schools = all_schools[:10]
                    
                    print(f"Found {len(all_schools)} schools within 5 miles")
                    
                    return {
                        'schools': all_schools,
                        'status': 'success'
                    }
                elif response.status_code == 429:
                    if attempt < 1:
                        print(f"Rate limited, waiting 5 seconds... (attempt {attempt + 1}/2)")
                        import time
                        time.sleep(5)
                    else:
                        print("Rate limit exceeded after all retries")
                        return {
                            'status': 'error',
                            'error_message': 'Rate limit exceeded. Please try again later.'
                        }
                else:
                    print(f"Overpass API returned status code: {response.status_code}")
                    if attempt < 1:
                        print(f"Retrying... (attempt {attempt + 1}/2)")
                        import time
                        time.sleep(5)
                    else:
                        return {
                            'status': 'error',
                            'error_message': f'API returned status code {response.status_code}'
                        }
                    
            except requests.exceptions.Timeout:
                print(f"Overpass API timeout on attempt {attempt + 1}/2")
                if attempt < 1:
                    print("Waiting 5 seconds before retry...")
                    import time
                    time.sleep(5)
                else:
                    return {
                        'status': 'error',
                        'error_message': 'API request timed out'
                    }
            except requests.exceptions.RequestException as e:
                print(f"Error fetching schools data: {e}")
                if attempt < 1:
                    print(f"Retrying... (attempt {attempt + 1}/2)")
                    import time
                    time.sleep(5)
                else:
                    return {
                        'status': 'error',
                        'error_message': 'Unable to connect to API'
                    }
        
    except Exception as e:
        print(f"Unexpected error fetching schools data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_healthcare_data(latitude, longitude):
    """
    Fetch nearby healthcare facilities using OpenStreetMap Overpass API
    Returns GP surgeries and hospitals within 10 miles
    Uses separate queries to avoid timeouts
    
    API: https://overpass-api.de/
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
    
    Returns:
        dict: Healthcare data with GP surgeries and hospitals
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for healthcare lookup'
            }
        
        print(f"Fetching healthcare data for coordinates: {latitude}, {longitude}")
        
        # REDUCED: 10 miles instead of 15
        TEN_MILES_IN_METERS = 16093
        
        # Overpass API endpoint
        url = 'https://overpass-api.de/api/interpreter'
        
        gp_surgeries = []
        hospitals = []
        
        # SPLIT QUERIES: Query GP surgeries separately
        gp_query = f"""
        [out:json][timeout:20];
        (
          node["amenity"="doctors"](around:{TEN_MILES_IN_METERS},{latitude},{longitude});
          way["amenity"="doctors"](around:{TEN_MILES_IN_METERS},{latitude},{longitude});
        );
        out center;
        """
        
        print(f"Querying GP surgeries with {TEN_MILES_IN_METERS}m radius")
        
        # RETRY LOGIC: Try up to 2 times (REDUCED from 4)
        for attempt in range(2):
            try:
                gp_response = requests.post(url, data={'data': gp_query}, timeout=25)
                
                if gp_response.status_code == 200:
                    gp_data = gp_response.json()
                    gp_elements = gp_data.get('elements', [])
                    print(f"Found {len(gp_elements)} GP surgeries")
                    
                    for element in gp_elements:
                        tags = element.get('tags', {})
                        name = tags.get('name', 'Unnamed Facility')
                        
                        if element.get('type') == 'node':
                            facility_lat = element.get('lat')
                            facility_lon = element.get('lon')
                        elif element.get('type') == 'way' and 'center' in element:
                            facility_lat = element['center'].get('lat')
                            facility_lon = element['center'].get('lon')
                        else:
                            continue
                        
                        distance_meters = calculate_distance(latitude, longitude, facility_lat, facility_lon)
                        distance_miles = round(distance_meters * 0.000621371, 2)
                        
                        if distance_miles > 10:
                            continue
                        
                        gp_surgeries.append({
                            'name': name,
                            'distance_miles': distance_miles,
                            'distance_meters': int(distance_meters),
                            'address': tags.get('addr:street', 'Address not available'),
                            'town': tags.get('addr:city', tags.get('addr:town', tags.get('addr:village', 'N/A')))
                        })
                    
                    break  # Success, exit retry loop
                    
                elif gp_response.status_code == 429:
                    if attempt < 1:
                        print(f"Rate limited, waiting 5 seconds before retry... (attempt {attempt + 1}/2)")
                        import time
                        time.sleep(5)
                    else:
                        print("Rate limit exceeded after all retries")
                else:
                    print(f"GP query failed with status {gp_response.status_code}")
                    if attempt < 1:
                        print(f"Retrying... (attempt {attempt + 1}/2)")
                        import time
                        time.sleep(5)
                    else:
                        break
                        
            except requests.exceptions.Timeout:
                print(f"GP query timeout on attempt {attempt + 1}/2")
                if attempt < 1:
                    print("Waiting 5 seconds before retry...")
                    import time
                    time.sleep(5)
                else:
                    print("Failed after all retries")
        
        # SPLIT QUERIES: Query hospitals separately
        hospital_query = f"""
        [out:json][timeout:20];
        (
          node["amenity"="hospital"](around:{TEN_MILES_IN_METERS},{latitude},{longitude});
          way["amenity"="hospital"](around:{TEN_MILES_IN_METERS},{latitude},{longitude});
        );
        out center;
        """
        
        print(f"Querying hospitals with {TEN_MILES_IN_METERS}m radius")
        
        # RETRY LOGIC: Try up to 2 times (REDUCED from 4)
        for attempt in range(2):
            try:
                hospital_response = requests.post(url, data={'data': hospital_query}, timeout=25)
                
                if hospital_response.status_code == 200:
                    hospital_data = hospital_response.json()
                    hospital_elements = hospital_data.get('elements', [])
                    print(f"Found {len(hospital_elements)} hospitals")
                    
                    for element in hospital_elements:
                        tags = element.get('tags', {})
                        name = tags.get('name', 'Unnamed Facility')
                        
                        if element.get('type') == 'node':
                            facility_lat = element.get('lat')
                            facility_lon = element.get('lon')
                        elif element.get('type') == 'way' and 'center' in element:
                            facility_lat = element['center'].get('lat')
                            facility_lon = element['center'].get('lon')
                        else:
                            continue
                        
                        distance_meters = calculate_distance(latitude, longitude, facility_lat, facility_lon)
                        distance_miles = round(distance_meters * 0.000621371, 2)
                        
                        if distance_miles > 10:
                            continue
                        
                        hospitals.append({
                            'name': name,
                            'distance_miles': distance_miles,
                            'distance_meters': int(distance_meters),
                            'address': tags.get('addr:street', 'Address not available'),
                            'town': tags.get('addr:city', tags.get('addr:town', tags.get('addr:village', 'N/A')))
                        })
                    
                    break  # Success, exit retry loop
                    
                elif hospital_response.status_code == 429:
                    if attempt < 1:
                        print(f"Rate limited on hospitals, waiting 5 seconds... (attempt {attempt + 1}/2)")
                        import time
                        time.sleep(5)
                    else:
                        print("Rate limit exceeded after all retries")
                else:
                    print(f"Hospital query failed with status {hospital_response.status_code}")
                    if attempt < 1:
                        print(f"Retrying... (attempt {attempt + 1}/2)")
                        import time
                        time.sleep(5)
                    else:
                        break
                        
            except requests.exceptions.Timeout:
                print(f"Hospital query timeout on attempt {attempt + 1}/2")
                if attempt < 1:
                    print("Waiting 5 seconds before retry...")
                    import time
                    time.sleep(5)
                else:
                    print("Failed after all retries")
        
        # Sort by distance and take top 5 (REDUCED from 10)
        gp_surgeries.sort(key=lambda x: x['distance_miles'])
        hospitals.sort(key=lambda x: x['distance_miles'])
        
        gp_surgeries = gp_surgeries[:5]
        hospitals = hospitals[:5]
        
        print(f"Returning: {len(gp_surgeries)} GP surgeries, {len(hospitals)} hospitals")
        
        return {
            'gp_surgeries': gp_surgeries,
            'hospitals': hospitals,
            'status': 'success'
        }
        
    except Exception as e:
        print(f"Unexpected error fetching healthcare data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_amenities_data(latitude, longitude):
    """
    Fetch nearby amenities using OpenStreetMap Overpass API
    Returns banks and post offices within 15 miles
    
    API: https://overpass-api.de/
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
    
    Returns:
        dict: Amenities data with banks and post offices
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for amenities lookup'
            }
        
        print(f"Fetching amenities data for coordinates: {latitude}, {longitude}")
        
        # Convert 15 miles to meters for the radius search
        FIFTEEN_MILES_IN_METERS = 24140
        
        # Overpass API endpoint
        url = 'https://overpass-api.de/api/interpreter'
        
        # Overpass QL query to find banks and post offices within 15 miles
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="bank"](around:{FIFTEEN_MILES_IN_METERS},{latitude},{longitude});
          way["amenity"="bank"](around:{FIFTEEN_MILES_IN_METERS},{latitude},{longitude});
          node["amenity"="post_office"](around:{FIFTEEN_MILES_IN_METERS},{latitude},{longitude});
          way["amenity"="post_office"](around:{FIFTEEN_MILES_IN_METERS},{latitude},{longitude});
        );
        out center;
        """
        
        print(f"Querying Overpass API for amenities with {FIFTEEN_MILES_IN_METERS}m radius")
        
        # RETRY LOGIC: Try up to 4 times
        for attempt in range(4):
            try:
                response = requests.post(url, data={'data': query}, timeout=30)
                
                print(f"Overpass API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get('elements', [])
                    
                    print(f"Found {len(elements)} amenities in total")
                    
                    if not elements:
                        return {
                            'banks': [],
                            'post_offices': [],
                            'status': 'success'
                        }
                    
                    # Process and categorize amenities
                    banks = []
                    post_offices = []
                    
                    for element in elements:
                        tags = element.get('tags', {})
                        amenity_type = tags.get('amenity', '')
                        name = tags.get('name', 'Unnamed')
                        
                        # Get coordinates (for ways, use center)
                        if element.get('type') == 'node':
                            amenity_lat = element.get('lat')
                            amenity_lon = element.get('lon')
                        elif element.get('type') == 'way' and 'center' in element:
                            amenity_lat = element['center'].get('lat')
                            amenity_lon = element['center'].get('lon')
                        else:
                            continue  # Skip if no coordinates
                        
                        # Calculate distance
                        distance_meters = calculate_distance(latitude, longitude, amenity_lat, amenity_lon)
                        distance_miles = round(distance_meters * 0.000621371, 2)
                        
                        # Only include if within 15 miles (double-check)
                        if distance_miles > 15:
                            continue
                        
                        amenity_info = {
                            'name': name,
                            'distance_miles': distance_miles,
                            'distance_meters': int(distance_meters),
                            'address': tags.get('addr:street', 'Address not available'),
                            'town': tags.get('addr:city', tags.get('addr:town', tags.get('addr:village', 'N/A')))
                        }
                        
                        # Categorize by amenity type
                        if amenity_type == 'bank':
                            banks.append(amenity_info)
                        elif amenity_type == 'post_office':
                            post_offices.append(amenity_info)
                    
                    # Sort by distance
                    banks.sort(key=lambda x: x['distance_miles'])
                    post_offices.sort(key=lambda x: x['distance_miles'])
                    
                    # Take top 10 banks and top 2 post offices
                    banks = banks[:10]
                    post_offices = post_offices[:2]
                    
                    print(f"Found: {len(banks)} banks, {len(post_offices)} post offices")
                    
                    return {
                        'banks': banks,
                        'post_offices': post_offices,
                        'status': 'success'
                    }
                elif response.status_code == 429:
                    if attempt < 3:
                        print(f"Rate limited, waiting 5 seconds... (attempt {attempt + 1}/4)")
                        import time
                        time.sleep(5)
                    else:
                        print("Rate limit exceeded after all retries")
                        return {
                            'status': 'error',
                            'error_message': 'Rate limit exceeded. Please try again later.'
                        }
                else:
                    print(f"Overpass API returned status code: {response.status_code}")
                    if attempt < 3:
                        print(f"Retrying... (attempt {attempt + 1}/4)")
                        import time
                        time.sleep(5)
                    else:
                        return {
                            'status': 'error',
                            'error_message': f'API returned status code {response.status_code}'
                        }
                    
            except requests.exceptions.Timeout:
                print(f"Amenities timeout on attempt {attempt + 1}/4")
                if attempt < 3:
                    print("Waiting 5 seconds before retry...")
                    import time
                    time.sleep(5)
                else:
                    return {
                        'status': 'error',
                        'error_message': 'API request timed out'
                    }
            except requests.exceptions.RequestException as e:
                print(f"Error fetching amenities data: {e}")
                if attempt < 3:
                    print(f"Retrying... (attempt {attempt + 1}/4)")
                    import time
                    time.sleep(5)
                else:
                    return {
                        'status': 'error',
                        'error_message': 'Unable to connect to API'
                    }
        
    except Exception as e:
        print(f"Unexpected error fetching amenities data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_lifestyle_amenities_data(latitude, longitude):
    """
    Fetch nearby lifestyle amenities using OpenStreetMap Overpass API
    Returns supermarkets, cafes, restaurants, and gyms within 10 miles
    Uses separate queries to avoid timeouts
    
    API: https://overpass-api.de/
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
    
    Returns:
        dict: Lifestyle amenities data
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available for lifestyle amenities lookup'
            }
        
        print(f"Fetching lifestyle amenities data for coordinates: {latitude}, {longitude}")
        
        # REDUCED: 10 miles instead of 15
        TEN_MILES_IN_METERS = 16093
        
        # Overpass API endpoint
        url = 'https://overpass-api.de/api/interpreter'
        
        supermarkets = []
        cafes = []
        restaurants = []
        gyms = []
        
        # Helper function for each amenity type with retry logic
        def fetch_amenity_type(amenity_name, query_type, tag_key, tag_value):
            results = []
            for attempt in range(2):  # RETRY LOGIC: 2 attempts (REDUCED from 4)
                try:
                    query = f"""
                    [out:json][timeout:20];
                    (
                      node["{tag_key}"="{tag_value}"](around:{TEN_MILES_IN_METERS},{latitude},{longitude});
                      way["{tag_key}"="{tag_value}"](around:{TEN_MILES_IN_METERS},{latitude},{longitude});
                    );
                    out center;
                    """
                    
                    print(f"Querying {amenity_name} (attempt {attempt + 1}/2)")
                    response = requests.post(url, data={'data': query}, timeout=25)
                    
                    if response.status_code == 200:
                        data = response.json()
                        elements = data.get('elements', [])
                        print(f"Found {len(elements)} {amenity_name}")
                        
                        for element in elements:
                            tags = element.get('tags', {})
                            name = tags.get('name', 'Unnamed')
                            
                            if element.get('type') == 'node':
                                amenity_lat = element.get('lat')
                                amenity_lon = element.get('lon')
                            elif element.get('type') == 'way' and 'center' in element:
                                amenity_lat = element['center'].get('lat')
                                amenity_lon = element['center'].get('lon')
                            else:
                                continue
                            
                            distance_meters = calculate_distance(latitude, longitude, amenity_lat, amenity_lon)
                            distance_miles = round(distance_meters * 0.000621371, 2)
                            
                            if distance_miles > 10:
                                continue
                            
                            results.append({
                                'name': name,
                                'distance_miles': distance_miles,
                                'distance_meters': int(distance_meters),
                                'address': tags.get('addr:street', 'Address not available'),
                                'town': tags.get('addr:city', tags.get('addr:town', tags.get('addr:village', 'N/A')))
                            })
                        
                        break  # Success
                        
                    elif response.status_code == 429:
                        if attempt < 1:
                            print(f"Rate limited on {amenity_name}, waiting 5 seconds... (attempt {attempt + 1}/2)")
                            import time
                            time.sleep(5)
                    else:
                        print(f"{amenity_name} query failed with status {response.status_code}")
                        if attempt < 1:
                            print(f"Retrying... (attempt {attempt + 1}/2)")
                            import time
                            time.sleep(5)
                        
                except requests.exceptions.Timeout:
                    print(f"{amenity_name} query timeout on attempt {attempt + 1}/2")
                    if attempt < 1:
                        print("Waiting 5 seconds before retry...")
                        import time
                        time.sleep(5)
                    
            return results
        
        # SPLIT QUERIES: Fetch each amenity type separately
        supermarkets = fetch_amenity_type("supermarkets", "shop", "shop", "supermarket")
        cafes = fetch_amenity_type("cafes", "amenity", "amenity", "cafe")
        restaurants = fetch_amenity_type("restaurants", "amenity", "amenity", "restaurant")
        
        # Gyms - need to combine sports_centre and fitness_centre
        gyms_sports = fetch_amenity_type("gyms (sports centres)", "leisure", "leisure", "sports_centre")
        gyms_fitness = fetch_amenity_type("gyms (fitness centres)", "leisure", "leisure", "fitness_centre")
        gyms = gyms_sports + gyms_fitness
        
        # Sort by distance and take top 5 (REDUCED NUMBER)
        supermarkets.sort(key=lambda x: x['distance_miles'])
        cafes.sort(key=lambda x: x['distance_miles'])
        restaurants.sort(key=lambda x: x['distance_miles'])
        gyms.sort(key=lambda x: x['distance_miles'])
        
        supermarkets = supermarkets[:5]
        cafes = cafes[:5]
        restaurants = restaurants[:5]
        gyms = gyms[:5]
        
        print(f"Returning: {len(supermarkets)} supermarkets, {len(cafes)} cafes, {len(restaurants)} restaurants, {len(gyms)} gyms")
        
        return {
            'supermarkets': supermarkets,
            'cafes': cafes,
            'restaurants': restaurants,
            'gyms': gyms,
            'status': 'success'
        }
        
    except Exception as e:
        print(f"Unexpected error fetching lifestyle amenities data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def normalize_address(address):
    """
    Normalize an address for comparison by:
    - Converting to lowercase
    - Removing punctuation
    - Removing extra whitespace
    - Standardizing common abbreviations
    
    Args:
        address (str): Raw address string
    
    Returns:
        str: Normalized address
    """
    if not address:
        return ""
    
    # Convert to lowercase
    addr = address.lower()
    
    # Remove punctuation except spaces
    import re
    addr = re.sub(r'[^\w\s]', ' ', addr)
    
    # Standardize common abbreviations
    replacements = {
        ' street ': ' st ',
        ' road ': ' rd ',
        ' avenue ': ' ave ',
        ' drive ': ' dr ',
        ' lane ': ' ln ',
        ' court ': ' ct ',
        ' place ': ' pl ',
        ' square ': ' sq ',
        ' terrace ': ' ter ',
        ' gardens ': ' gdns ',
        ' crescent ': ' cres ',
        ' close ': ' cl ',
        'flat ': 'flat',
        'apartment ': 'apt',
    }
    
    for old, new in replacements.items():
        addr = addr.replace(old, new)
    
    # Remove extra whitespace
    addr = ' '.join(addr.split())
    
    return addr


def address_matches(address1, address2):
    """
    Check if two normalized addresses match
    Uses fuzzy matching to account for slight variations
    
    Args:
        address1 (str): First normalized address
        address2 (str): Second normalized address
    
    Returns:
        bool: True if addresses likely match
    """
    if not address1 or not address2:
        return False
    
    # Extract numeric parts (building numbers)
    import re
    numbers1 = set(re.findall(r'\d+', address1))
    numbers2 = set(re.findall(r'\d+', address2))
    
    # If both have numbers, they must have at least one in common
    if numbers1 and numbers2:
        if not numbers1.intersection(numbers2):
            return False
    
    # Split into words
    words1 = set(address1.split())
    words2 = set(address2.split())
    
    # Calculate word overlap
    common_words = words1.intersection(words2)
    total_words = len(words1.union(words2))
    
    if total_words == 0:
        return False
    
    # If more than 60% of words match, consider it a match
    overlap_ratio = len(common_words) / total_words
    
    # Also check if address2 contains most of address1 (for partial matches)
    words1_in_address2 = sum(1 for word in words1 if word in address2)
    contains_ratio = words1_in_address2 / len(words1) if words1 else 0
    
    print(f"    Overlap: {overlap_ratio:.2%}, Contains: {contains_ratio:.2%}")
    
    return overlap_ratio >= 0.6 or contains_ratio >= 0.7


def convert_to_british_national_grid(latitude, longitude):
    """
    Convert WGS84 (lat/long) to British National Grid (EPSG:27700)
    Uses custom conversion algorithm compatible with Python 3.13
    
    Args:
        latitude (float): WGS84 latitude
        longitude (float): WGS84 longitude
    
    Returns:
        tuple: (easting, northing) in British National Grid
    """
    try:
        import math
        
        # WGS84 to OSGB36 conversion parameters (Helmert transformation)
        # This is a simplified conversion that works for most of UK
        
        # Convert to radians
        lat = math.radians(latitude)
        lon = math.radians(longitude)
        
        # WGS84 ellipsoid parameters
        a = 6378137.0  # Semi-major axis
        b = 6356752.314245  # Semi-minor axis
        e2 = (a*a - b*b) / (a*a)  # First eccentricity squared
        
        # Transverse Mercator projection parameters for OSGB
        lat0 = math.radians(49.0)  # True origin latitude
        lon0 = math.radians(-2.0)  # True origin longitude
        N0 = -100000.0  # Northing of true origin
        E0 = 400000.0  # Easting of true origin
        F0 = 0.9996012717  # Scale factor on central meridian
        
        # Calculate transverse Mercator projection
        n = (a - b) / (a + b)
        n2 = n * n
        n3 = n * n * n
        
        # Meridional arc
        sinlat = math.sin(lat)
        coslat = math.cos(lat)
        nu = a * F0 / math.sqrt(1 - e2 * sinlat * sinlat)
        rho = a * F0 * (1 - e2) / math.pow(1 - e2 * sinlat * sinlat, 1.5)
        eta2 = nu / rho - 1
        
        # Longitude difference from central meridian
        dlon = lon - lon0
        
        # Meridional arc calculation
        M = b * F0 * (
            (1 + n + (5/4)*n2 + (5/4)*n3) * (lat - lat0)
            - (3*n + 3*n2 + (21/8)*n3) * math.sin(lat - lat0) * math.cos(lat + lat0)
            + ((15/8)*n2 + (15/8)*n3) * math.sin(2*(lat - lat0)) * math.cos(2*(lat + lat0))
            - (35/24)*n3 * math.sin(3*(lat - lat0)) * math.cos(3*(lat + lat0))
        )
        
        # Easting
        I = M + N0
        II = (nu/2) * sinlat * coslat
        III = (nu/24) * sinlat * coslat * coslat * coslat * (5 - sinlat*sinlat + 9*eta2)
        IIIA = (nu/720) * sinlat * coslat**5 * (61 - 58*sinlat*sinlat + sinlat**4)
        
        northing = I + II*dlon*dlon + III*dlon**4 + IIIA*dlon**6
        
        # Northing
        IV = nu * coslat
        V = (nu/6) * coslat**3 * (nu/rho - sinlat*sinlat)
        VI = (nu/120) * coslat**5 * (5 - 18*sinlat*sinlat + sinlat**4 + 14*eta2 - 58*sinlat*sinlat*eta2)
        
        easting = E0 + IV*dlon + V*dlon**3 + VI*dlon**5
        
        print(f"Coordinate conversion successful: ({latitude}, {longitude}) -> ({easting:.2f}, {northing:.2f})")
        
        return easting, northing
        
    except Exception as e:
        print(f"Error converting coordinates: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def fetch_listed_building_status(latitude, longitude, address):
    """
    Check if property is a listed building using Historic England API
    Uses address matching to verify the correct property
    
    API: https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Listed_Building_points/FeatureServer/0
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
        address (str): Full address of the property to match against
    
    Returns:
        dict: Listed building status and details
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available'
            }
        
        print(f"Checking listed building status for coordinates: {latitude}, {longitude}")
        print(f"Target address for matching: {address}")
        
        # Convert to British National Grid
        easting, northing = convert_to_british_national_grid(latitude, longitude)
        
        if easting is None or northing is None:
            return {
                'status': 'error',
                'error_message': 'Coordinate conversion failed'
            }
        
        print(f"Converted to BNG: {easting}, {northing}")
        
        # Historic England ArcGIS REST API endpoint for listed buildings (points)
        url = "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Listed_Building_points/FeatureServer/0/query"
        
        params = {
            'geometry': f'{{"x":{easting},"y":{northing},"spatialReference":{{"wkid":27700}}}}',
            'geometryType': 'esriGeometryPoint',
            'inSR': '27700',
            'spatialRel': 'esriSpatialRelIntersects',
            'distance': 50,  # Search within 50 meters
            'units': 'esriSRUnit_Meter',
            'outFields': '*',
            'returnGeometry': 'false',
            'f': 'json'
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            if features:
                print(f"Found {len(features)} listed building(s) within 50m")
                
                # Try to match the address with one of the found buildings
                matched_building = None
                
                # Normalize the target address for comparison
                target_address_normalized = normalize_address(address)
                
                for feature in features:
                    building = feature['attributes']
                    
                    # Get address components from the API
                    building_address_parts = []
                    
                    # Historic England API may have these address fields
                    if building.get('Location'):
                        building_address_parts.append(building.get('Location'))
                    if building.get('FullAddress'):
                        building_address_parts.append(building.get('FullAddress'))
                    if building.get('ADDRESS'):
                        building_address_parts.append(building.get('ADDRESS'))
                    
                    # Create a combined address string
                    building_address = ' '.join(filter(None, building_address_parts))
                    building_address_normalized = normalize_address(building_address)
                    
                    print(f"Comparing:")
                    print(f"  Target: {target_address_normalized}")
                    print(f"  Building: {building_address_normalized}")
                    
                    # Check if addresses match (fuzzy match)
                    if address_matches(target_address_normalized, building_address_normalized):
                        matched_building = building
                        print(f"  ✓ MATCH FOUND!")
                        break
                    else:
                        print(f"  ✗ No match")
                
                if matched_building:
                    # Found a matching listed building!
                    print(f"Confirmed: Property is listed building - {matched_building.get('Name', 'Unnamed')}, Grade {matched_building.get('Grade', 'Unknown')}")
                    
                    return {
                        'status': 'success',
                        'is_listed': True,
                        'name': matched_building.get('Name', 'Unnamed Building'),
                        'grade': matched_building.get('Grade', 'Unknown'),
                        'list_entry': matched_building.get('ListEntry'),
                        'date_listed': matched_building.get('ListDate', 'Unknown')
                    }
                else:
                    # Found listed buildings nearby but none match this address
                    print(f"Found {len(features)} listed building(s) nearby but none match the target address")
                    return {
                        'status': 'success',
                        'is_listed': False
                    }
            else:
                # Not a listed building
                print("No listed buildings found within 50m")
                return {
                    'status': 'success',
                    'is_listed': False
                }
        else:
            print(f"Historic England API returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("Historic England API timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching listed building data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error checking listed building status: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_conservation_area_status(latitude, longitude):
    """
    Check if property is in a conservation area using Historic England API
    
    API: https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Conservation_Areas/FeatureServer/0
    
    Args:
        latitude (float): Property latitude
        longitude (float): Property longitude
    
    Returns:
        dict: Conservation area status and details
    """
    try:
        if latitude is None or longitude is None:
            return {
                'status': 'error',
                'error_message': 'No coordinates available'
            }
        
        print(f"Checking conservation area status for coordinates: {latitude}, {longitude}")
        
        # Convert to British National Grid
        easting, northing = convert_to_british_national_grid(latitude, longitude)
        
        if easting is None or northing is None:
            return {
                'status': 'error',
                'error_message': 'Coordinate conversion failed'
            }
        
        print(f"Converted to BNG: {easting}, {northing}")
        
        # Historic England ArcGIS REST API endpoint for conservation areas
        url = "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Conservation_Areas/FeatureServer/0/query"
        
        params = {
            'geometry': f'{{"x":{easting},"y":{northing},"spatialReference":{{"wkid":27700}}}}',
            'geometryType': 'esriGeometryPoint',
            'inSR': '27700',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'false',
            'f': 'json'
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            if features:
                # Property is in a conservation area!
                area = features[0]['attributes']
                
                # Debug: print all available attributes (can be removed later)
                print(f"Conservation Area attributes returned by API:")
                for key, value in area.items():
                    print(f"  {key}: {value}")
                
                # Extract using correct field names from Historic England API
                area_name = area.get('NAME', 'Unnamed Conservation Area')
                local_authority = area.get('LPA', 'Unknown')
                
                # Date field - convert to readable format if it's a year
                date_designated = area.get('DATE_OF_DE', 'Unknown')
                if date_designated and date_designated != 'Unknown' and str(date_designated).isdigit():
                    date_designated = str(date_designated)  # Keep as year
                
                print(f"Extracted: Name='{area_name}', Authority='{local_authority}', Date='{date_designated}'")
                
                return {
                    'status': 'success',
                    'in_conservation_area': True,
                    'area_name': area_name,
                    'local_authority': local_authority,
                    'date_designated': date_designated
                }
            else:
                # Not in a conservation area
                print("Property is not in a conservation area")
                return {
                    'status': 'success',
                    'in_conservation_area': False
                }
        else:
            print(f"Historic England API returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("Historic England API timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching conservation area data: {e}")
        return {
            'status': 'error',
            'error_message': 'Unable to connect to API'
        }
    except Exception as e:
        print(f"Unexpected error checking conservation area status: {e}")
        return {
            'status': 'error',
            'error_message': 'An unexpected error occurred'
        }


def fetch_all_data(postcode, address):
    """
    Coordinate all API calls and combine the results
    
    This function calls each individual API function and combines
    the results into a single dictionary for easy access.
    
    Args:
        postcode (str): The UK postcode to fetch data for
        address (str): The full address selected by the user
        
    Returns:
        dict: Combined data from all APIs
    """
    data = {}
    
    print(f"=== FETCH ALL DATA ===")
    print(f"Postcode received: {postcode}")
    print(f"Address received: {address}")
    
    # Fetch location data first (we need coordinates for other APIs)
    data['location'] = fetch_location_data(postcode)
    
    # Get coordinates for subsequent API calls
    location = data['location']
    if location.get('status') == 'success':
        latitude = location.get('latitude')
        longitude = location.get('longitude')
        admin_district = location.get('admin_district', '')
        
        # Fetch crime data using coordinates
        data['crime'] = fetch_crime_data(latitude, longitude)
        data['train_station'] = fetch_train_station_data(latitude, longitude)
        data['bus_stop'] = fetch_bus_stop_data(latitude, longitude)
        data['tube_station'] = fetch_tube_station_data(latitude, longitude)
        data['tram_stop'] = fetch_tram_stop_data(latitude, longitude)
        data['nearest_station'] = fetch_nearest_station_info(latitude, longitude, admin_district)
        data['schools'] = fetch_schools_data(latitude, longitude)
        data['healthcare'] = fetch_healthcare_data(latitude, longitude)
        data['lifestyle'] = fetch_lifestyle_amenities_data(latitude, longitude)
        
        # Historic England data - Listed Buildings and Conservation Areas
        data['listed_building'] = fetch_listed_building_status(latitude, longitude, address)
        data['conservation_area'] = fetch_conservation_area_status(latitude, longitude)
    else:
        data['crime'] = {
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['train_station'] = {
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['bus_stop'] = {
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['tube_station'] = {
            'status': 'none_nearby'
        }
        data['tram_stop'] = {
            'status': 'none_nearby'
        }
        data['nearest_station'] = {
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['schools'] = {
            'schools': [],
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['healthcare'] = {
            'gp_surgeries': [],
            'hospitals': [],
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['lifestyle'] = {
            'supermarkets': [],
            'cafes': [],
            'restaurants': [],
            'gyms': [],
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['listed_building'] = {
            'status': 'error',
            'error_message': 'No coordinates available'
        }
        data['conservation_area'] = {
            'status': 'error',
            'error_message': 'No coordinates available'
        }
    
    # EPC data (council tax band, energy rating, etc.) - pass address for matching
    print(f"Calling EPC API with postcode: {postcode} and address: {address}")
    data['epc'] = fetch_epc_data(postcode, address)
    
    # Land Registry Price Paid Data (property sale history)
    print(f"Calling Land Registry Price Paid API for property sale history")
    data['price_paid'] = fetch_price_paid_data(postcode, address)
    
    return data



def fetch_price_paid_data(postcode, address):
    """
    Fetch Land Registry Price Paid Data for a specific property.
    Shows when the property was last sold and for how much.
    
    Args:
        postcode (str): Property postcode
        address (str): Property address (for matching)
    
    Returns:
        dict: Price paid transaction data
    """
    try:
        if not postcode or not address:
            return {
                'status': 'error',
                'error_message': 'No postcode or address available'
            }
        
        print(f"Fetching Land Registry price paid data for postcode: {postcode}")
        
        # Clean the postcode (remove spaces for API)
        postcode_clean = postcode.replace(' ', '%20')
        
        # Land Registry Linked Data API endpoint
        # Query by postcode to get all transactions
        url = f"http://landregistry.data.gov.uk/data/ppi/address.json?postcode={postcode_clean}"
        
        print(f"Land Registry API URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # The API returns a list of results
            results = data.get('result', {}).get('items', [])
            
            if not results:
                print("No price paid data found for this postcode")
                return {
                    'status': 'success',
                    'transactions': [],
                    'property_found': False
                }
            
            print(f"Found {len(results)} transactions in this postcode")
            
            # Normalize target address for matching
            target_address_normalized = normalize_address(address)
            print(f"Target address for matching: {target_address_normalized}")
            
            # Find transactions that match this specific property
            property_transactions = []
            
            for item in results:
                # Extract address components from the transaction
                property_address = item.get('propertyAddress', {})
                
                # Build full address string from components
                address_parts = []
                
                # PAON (Primary Addressable Object Name) - house number/name
                paon = property_address.get('paon', '')
                if paon:
                    address_parts.append(paon)
                
                # SAON (Secondary Addressable Object Name) - flat number
                saon = property_address.get('saon', '')
                if saon:
                    address_parts.append(saon)
                
                # Street
                street = property_address.get('street', '')
                if street:
                    address_parts.append(street)
                
                # Town
                town = property_address.get('town', '')
                if town:
                    address_parts.append(town)
                
                # Build complete address
                transaction_address = ' '.join(address_parts)
                transaction_address_normalized = normalize_address(transaction_address)
                
                print(f"Comparing transaction address: {transaction_address_normalized}")
                
                # Check if this transaction matches our property
                if address_matches(target_address_normalized, transaction_address_normalized):
                    # Extract transaction details
                    transaction = {
                        'price': item.get('pricePaid', 0),
                        'date': item.get('transactionDate', 'Unknown'),
                        'property_type': item.get('propertyType', 'Unknown'),
                        'new_build': item.get('newBuild', False),
                        'tenure': item.get('estateType', 'Unknown'),
                        'address': transaction_address
                    }
                    
                    property_transactions.append(transaction)
                    print(f"✓ MATCH FOUND! Price: £{transaction['price']:,}, Date: {transaction['date']}")
            
            # Sort transactions by date (most recent first)
            property_transactions.sort(key=lambda x: x['date'], reverse=True)
            
            if property_transactions:
                print(f"Found {len(property_transactions)} transaction(s) for this specific property")
                return {
                    'status': 'success',
                    'property_found': True,
                    'transactions': property_transactions,
                    'most_recent': property_transactions[0] if property_transactions else None
                }
            else:
                print("No transactions found matching this specific property address")
                return {
                    'status': 'success',
                    'property_found': False,
                    'transactions': []
                }
        else:
            print(f"Land Registry API returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("Land Registry API timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except Exception as e:
        print(f"Error fetching Land Registry price paid data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': str(e)
        }


def fetch_current_flood_warnings(county=None):
    """
    Fetch current flood warnings from Environment Agency.
    Shows real-time flood warnings and alerts.
    
    Args:
        county (str): Optional county name to filter results (e.g., 'Wiltshire')
    
    Returns:
        dict: Current flood warning status and details
    """
    try:
        print(f"Fetching current flood warnings{' for ' + county if county else ''}...")
        
        # Environment Agency Flood Monitoring API
        if county:
            url = f"https://environment.data.gov.uk/flood-monitoring/id/floods?county={county}"
        else:
            url = "https://environment.data.gov.uk/flood-monitoring/id/floods"
        
        print(f"Flood API URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            warnings = data.get('items', [])
            
            if not warnings:
                print("No flood warnings currently in force")
                return {
                    'status': 'success',
                    'warnings_active': False,
                    'warning_count': 0,
                    'message': 'No flood warnings currently in force'
                }
            
            print(f"Found {len(warnings)} flood warning(s)")
            
            # Process warnings
            processed_warnings = []
            
            for warning in warnings:
                severity_level = warning.get('severityLevel', 4)
                
                processed_warnings.append({
                    'description': warning.get('description', 'Unknown location'),
                    'severity': warning.get('severity', 'Unknown'),
                    'severity_level': severity_level,
                    'message': warning.get('message', ''),
                    'time_raised': warning.get('timeRaised', 'Unknown'),
                    'area_name': warning.get('eaAreaName', 'Unknown')
                })
            
            # Sort by severity (1 = most severe)
            processed_warnings.sort(key=lambda x: x['severity_level'])
            
            return {
                'status': 'success',
                'warnings_active': True,
                'warning_count': len(processed_warnings),
                'warnings': processed_warnings,
                'most_severe': processed_warnings[0] if processed_warnings else None
            }
        else:
            print(f"Flood API returned status code: {response.status_code}")
            return {
                'status': 'error',
                'error_message': f'API returned status code {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        print("Flood API timeout")
        return {
            'status': 'error',
            'error_message': 'API request timed out'
        }
    except Exception as e:
        print(f"Error fetching flood warnings: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': str(e)
        }


def get_long_term_flood_risk(postcode):
    """
    Get long-term flood risk classification from local database.
    Shows Flood Zone classification and various flood risks.
    
    Args:
        postcode (str): Property postcode
    
    Returns:
        dict: Long-term flood risk data
    """
    try:
        import sqlite3
        import os
        
        print(f"Looking up long-term flood risk for postcode: {postcode}")
        
        # Clean postcode
        postcode_clean = postcode.replace(' ', '').upper()
        
        # Database path
        username = os.path.expanduser('~').split('/')[-1]
        db_path = f'/home/{username}/data/flood_risk.db'
        
        # Check if database exists
        if not os.path.exists(db_path):
            print(f"Flood risk database not found at {db_path}")
            return {
                'status': 'error',
                'error_message': 'Flood risk database not available. Please run setup_flood_database.py'
            }
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query database
        cursor.execute('SELECT * FROM flood_risk WHERE postcode = ?', (postcode_clean,))
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            print(f"Postcode {postcode_clean} not found in flood risk database")
            return {
                'status': 'not_found',
                'error_message': f'Flood risk data not available for postcode {postcode}'
            }
        
        # Extract data
        postcode, rofrs_high, rofrs_medium, rofrs_low, rofsw_high, rofsw_medium, rofsw_low, groundwater, reservoirs = result
        
        print(f"Found flood risk data for {postcode}:")
        print(f"  Rivers/Sea - High: {rofrs_high}, Medium: {rofrs_medium}, Low: {rofrs_low}")
        print(f"  Surface Water - High: {rofsw_high}, Medium: {rofsw_medium}, Low: {rofsw_low}")
        print(f"  Groundwater: {groundwater}, Reservoirs: {reservoirs}")
        
        # Determine overall risk from rivers and sea
        if rofrs_high > 0:
            river_sea_risk = 'High'
            river_sea_zone = 'Flood Zone 3'
            river_sea_probability = '>1% (greater than 1 in 100 annual chance)'
        elif rofrs_medium > 0:
            river_sea_risk = 'Medium'
            river_sea_zone = 'Flood Zone 2'
            river_sea_probability = '0.1% - 1% (1 in 100 to 1 in 1000 annual chance)'
        elif rofrs_low > 0:
            river_sea_risk = 'Low'
            river_sea_zone = 'Flood Zone 1'
            river_sea_probability = '<0.1% (less than 1 in 1000 annual chance)'
        else:
            river_sea_risk = 'Very Low'
            river_sea_zone = 'Flood Zone 1'
            river_sea_probability = '<0.1% (less than 1 in 1000 annual chance)'
        
        # Determine surface water risk
        if rofsw_high > 0:
            surface_water_risk = 'High'
            surface_water_probability = '>3.3% (greater than 1 in 30 annual chance)'
        elif rofsw_medium > 0:
            surface_water_risk = 'Medium'
            surface_water_probability = '1% - 3.3% (1 in 100 to 1 in 30 annual chance)'
        elif rofsw_low > 0:
            surface_water_risk = 'Low'
            surface_water_probability = '0.1% - 1% (1 in 1000 to 1 in 100 annual chance)'
        else:
            surface_water_risk = 'Very Low'
            surface_water_probability = '<0.1% (less than 1 in 1000 annual chance)'
        
        return {
            'status': 'success',
            'river_sea_risk': river_sea_risk,
            'river_sea_zone': river_sea_zone,
            'river_sea_probability': river_sea_probability,
            'surface_water_risk': surface_water_risk,
            'surface_water_probability': surface_water_probability,
            'groundwater_risk': groundwater,
            'reservoir_risk': reservoirs,
            'raw_data': {
                'rofrs_high': rofrs_high,
                'rofrs_medium': rofrs_medium,
                'rofrs_low': rofrs_low,
                'rofsw_high': rofsw_high,
                'rofsw_medium': rofsw_medium,
                'rofsw_low': rofsw_low
            }
        }
        
    except Exception as e:
        print(f"Error getting long-term flood risk: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error_message': str(e)
        }

