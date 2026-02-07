from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from io import BytesIO
from datetime import datetime


# Professional Color Scheme
COLORS = {
    'primary': HexColor('#2C5F8D'),      # Deep blue - main headings
    'secondary': HexColor('#4A90A4'),    # Lighter blue - subheadings
    'accent': HexColor('#E8704C'),       # Coral - highlights/warnings
    'success': HexColor('#4A9D5F'),      # Green - positive indicators
    'warning': HexColor('#F39C12'),      # Orange - caution
    'danger': HexColor('#E74C3C'),       # Red - alerts
    'dark_gray': HexColor('#34495E'),    # Dark gray - body text
    'light_gray': HexColor('#95A5A6'),   # Light gray - secondary text
    'bg_light': HexColor('#ECF0F1'),     # Very light gray - backgrounds
}


def draw_section_header(pdf, x, y, text, width_inches=7):
    """
    Draw a colored section header with background
    Returns the new y position after the header
    """
    pdf.setFillColor(COLORS['secondary'])
    pdf.rect(x - 0.1*inch, y - 0.05*inch, width_inches*inch, 0.3*inch, fill=True, stroke=False)
    
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x, y, text)
    pdf.setFillColor(COLORS['dark_gray'])
    
    return y - 0.35*inch


def draw_subsection_header(pdf, x, y, text):
    """
    Draw a colored subsection header (no background, just colored text)
    Returns the new y position after the header
    """
    pdf.setFillColor(COLORS['primary'])
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x, y, text)
    pdf.setFillColor(COLORS['dark_gray'])
    
    return y - 0.25*inch


def create_pdf(first_name, last_name, postcode, address, data):
    """
    Create a formatted PDF from the data
    Returns a BytesIO buffer containing the PDF
    """
    # Create a buffer to store the PDF in memory
    buffer = BytesIO()
    
    # Create PDF canvas
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # ===== HEADER WITH COLORED BACKGROUND =====
    # Draw colored header bar
    pdf.setFillColor(COLORS['primary'])
    pdf.rect(0, height - 1.5*inch, width, 1.5*inch, fill=True, stroke=False)
    
    # Title in white
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(1*inch, height - 0.8*inch, "UK Property Report")
    
    # Reset to dark gray for body text
    pdf.setFillColor(COLORS['dark_gray'])
    
    # Generated for text
    pdf.setFont("Helvetica", 12)
    full_name = f"{first_name} {last_name}"
    pdf.drawString(1*inch, height - 1.6*inch, f"This report was generated for {full_name}")
    
    # Address in UK format
    pdf.setFont("Helvetica", 11)
    y_pos = height - 1.9*inch
    
    # Split address by commas and display line by line
    address_parts = [part.strip() for part in address.split(',')]
    for part in address_parts:
        pdf.drawString(1*inch, y_pos, part)
        y_pos -= 0.2*inch
    
    # Starting position for content
    y_position = y_pos - 0.3*inch
    
    # ===== LOCATION INFORMATION SECTION =====
    # Section heading with colored background
    pdf.setFillColor(COLORS['secondary'])
    pdf.rect(0.9*inch, y_position - 0.05*inch, width - 1.8*inch, 0.3*inch, fill=True, stroke=False)
    
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(1*inch, y_position, "Location Information")
    pdf.setFillColor(COLORS['dark_gray'])
    y_position -= 0.35*inch
    
    pdf.setFont("Helvetica", 12)
    location = data.get('location', {})
    
    if location.get('status') == 'success':
        # Successfully retrieved data from API
        pdf.drawString(1.2*inch, y_position, f"Country: {location.get('country', 'N/A')}")
        y_position -= 0.25*inch
        pdf.drawString(1.2*inch, y_position, f"Region: {location.get('region', 'N/A')}")
        y_position -= 0.25*inch
        pdf.drawString(1.2*inch, y_position, f"County: {location.get('admin_district', 'N/A')}")
        y_position -= 0.25*inch
        
        # Handle long parliamentary constituency text
        constituency = location.get('parliamentary_constituency', 'N/A')
        if len(constituency) > 50:
            pdf.drawString(1.2*inch, y_position, f"Parliamentary Constituency:")
            y_position -= 0.2*inch
            pdf.drawString(1.4*inch, y_position, constituency)
        else:
            pdf.drawString(1.2*inch, y_position, f"Parliamentary Constituency: {constituency}")
        y_position -= 0.25*inch
        
        # Handle parish (can be long text)
        parish = location.get('parish', 'N/A')
        if parish and len(parish) > 50:
            pdf.drawString(1.2*inch, y_position, f"Parish:")
            y_position -= 0.2*inch
            pdf.drawString(1.4*inch, y_position, parish)
        else:
            pdf.drawString(1.2*inch, y_position, f"Parish: {parish if parish else 'N/A'}")
        y_position -= 0.25*inch
        
        pdf.drawString(1.2*inch, y_position, f"Coordinates: {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}")
    elif location.get('status') == 'error':
        # API error occurred
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Location data unavailable: {location.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
    else:
        # No data returned
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Location data unavailable")
        pdf.setFont("Helvetica", 12)
    
    y_position -= 0.5*inch
    
    # Check if we need a new page (if y_position is too low)
    if y_position < 4*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    y_position -= 0.3*inch
    
    # ===== CRIME STATISTICS SECTION =====
    y_position = draw_section_header(pdf, 1*inch, y_position, "Crime Statistics")
    
    # Add explanatory text about coverage area
    pdf.setFont("Helvetica-Oblique", 10)
    location_info = data.get('location', {})
    if location_info.get('status') == 'success':
        town = location_info.get('admin_district', 'the area')
        pdf.drawString(1.2*inch, y_position, f"Crime data for approximately 1-mile radius around this location in {town}")
    else:
        pdf.drawString(1.2*inch, y_position, f"Crime data for approximately 1-mile radius around this location")
    y_position -= 0.25*inch
    
    pdf.setFont("Helvetica", 12)
    crime = data.get('crime', {})
    
    if crime.get('status') == 'success':
        # Display monthly crime totals
        monthly_totals = crime.get('monthly_totals', [])
        
        if monthly_totals:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(1.2*inch, y_position, "Monthly Crime Totals:")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica", 11)
            for month_data in monthly_totals:
                month = month_data['month']
                count = month_data['count']
                pdf.drawString(1.4*inch, y_position, f"{month}: {count} crimes")
                y_position -= 0.2*inch
            
            y_position -= 0.2*inch
            
            # Show crime breakdown for latest month only
            period = crime.get('period', 'N/A')
            crime_types = crime.get('crime_types', {})
            
            if crime_types:
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawString(1.2*inch, y_position, f"Crime Breakdown for {period}:")
                y_position -= 0.25*inch
                
                pdf.setFont("Helvetica", 11)
                
                # Show top 10 crime types
                for crime_type, count in list(crime_types.items())[:10]:
                    if y_position < 2*inch:
                        pdf.showPage()
                        y_position = height - 1*inch
                    
                    pdf.drawString(1.4*inch, y_position, f"{crime_type}: {count}")
                    y_position -= 0.2*inch
                
                if len(crime_types) > 10:
                    pdf.setFont("Helvetica-Oblique", 10)
                    pdf.drawString(1.4*inch, y_position, f"...and {len(crime_types) - 10} more types")
                    y_position -= 0.2*inch
        else:
            pdf.setFont("Helvetica-Oblique", 11)
            pdf.drawString(1.2*inch, y_position, "No crime data available for this area")
            pdf.setFont("Helvetica", 12)
            
    elif crime.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Crime data unavailable: {crime.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Crime data unavailable")
        pdf.setFont("Helvetica", 12)
    
    y_position -= 0.5*inch
    
    # Check if we need a new page
    if y_position < 3*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    # Nearest Station Information Section
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(1*inch, y_position, "Nearest Train Station")
    y_position -= 0.3*inch
    
    pdf.setFont("Helvetica", 12)
    station_info = data.get('nearest_station', {})
    
    if station_info.get('status') == 'success':
        station_name = station_info.get('station_name', 'N/A')
        station_code = station_info.get('station_code', 'N/A')
        distance_miles = station_info.get('distance_miles', 0)
        destination = station_info.get('typical_destination', 'N/A')
        
        pdf.drawString(1.2*inch, y_position, f"Station: {station_name} ({station_code})")
        y_position -= 0.25*inch
        pdf.drawString(1.2*inch, y_position, f"Distance: {distance_miles} miles from property")
        y_position -= 0.25*inch
        pdf.drawString(1.2*inch, y_position, f"Typical destination: {destination}")
        y_position -= 0.25*inch
    elif station_info.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Station data unavailable: {station_info.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Station data unavailable")
        pdf.setFont("Helvetica", 12)
    
    y_position -= 0.5*inch
    
    # Check if we need a new page
    if y_position < 3*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    # ===== PROPERTY INFORMATION SECTION =====
    y_position = draw_section_header(pdf, 1*inch, y_position, "Property Information")
    
    pdf.setFont("Helvetica", 12)
    epc = data.get('epc', {})
    
    if epc.get('status') == 'success':
        # Display EPC data
        if epc.get('energy_rating'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Energy Rating: {epc.get('energy_rating', 'N/A')}")
            y_position -= 0.25*inch
        
        if epc.get('potential_energy_rating'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Potential Energy Rating: {epc.get('potential_energy_rating', 'N/A')}")
            y_position -= 0.25*inch
        
        if epc.get('property_type'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Property Type: {epc.get('property_type', 'N/A')}")
            y_position -= 0.25*inch
        
        if epc.get('built_form'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Built Form: {epc.get('built_form', 'N/A')}")
            y_position -= 0.25*inch
        
        if epc.get('construction_age_band'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Construction Age: {epc.get('construction_age_band', 'N/A')}")
            y_position -= 0.25*inch
        
        if epc.get('total_floor_area'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Total Floor Area: {epc.get('total_floor_area', 'N/A')} m²")
            y_position -= 0.25*inch
        
        if epc.get('inspection_date'):
            if y_position < 1.5*inch:
                pdf.showPage()
                y_position = height - 1*inch
            pdf.drawString(1.2*inch, y_position, f"Last EPC Inspection: {epc.get('inspection_date', 'N/A')}")
            y_position -= 0.25*inch
    elif epc.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Property data unavailable: {epc.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Property data unavailable")
        pdf.setFont("Helvetica", 12)
    
    y_position -= 0.5*inch
    
    # Check if we need a new page before train station section
    if y_position < 2*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    # ===== TRAIN STATION SECTION =====
    y_position = draw_section_header(pdf, 1*inch, y_position, "Nearest Train Stations")
    
    pdf.setFont("Helvetica", 12)
    station_data = data.get('train_station', {})
    
    if station_data.get('status') == 'success':
        stations = station_data.get('stations', [])
        
        if stations:
            for i, station in enumerate(stations, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = station.get('name', 'N/A')
                distance = station.get('distance', 0)
                station_code = station.get('station_code', 'N/A')
                
                # Convert distance from meters to miles
                distance_miles = round(distance * 0.000621371, 2) if distance else 0
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles ({distance}m)")
                y_position -= 0.18*inch
                pdf.drawString(1.4*inch, y_position, f"Station Code: {station_code}")
                y_position -= 0.25*inch
        else:
            pdf.setFont("Helvetica-Oblique", 11)
            pdf.drawString(1.2*inch, y_position, "No train stations found nearby")
            pdf.setFont("Helvetica", 12)
    elif station_data.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Train station data unavailable: {station_data.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Train station data unavailable")
        pdf.setFont("Helvetica", 12)
    
    y_position -= 0.5*inch
    
    # Check if we need a new page
    if y_position < 2*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    # London Underground Section (only show if within 3 miles)
    tube_data = data.get('tube_station', {})
    
    if tube_data.get('status') == 'success':
        stations = tube_data.get('stations', [])
        
        if stations:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearest London Underground Stations")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, station in enumerate(stations, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = station.get('name', 'N/A')
                distance = station.get('distance', 0)
                station_code = station.get('station_code', 'N/A')
                
                # Convert distance from meters to miles
                distance_miles = round(distance * 0.000621371, 2) if distance else 0
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles ({distance}m)")
                y_position -= 0.18*inch
                pdf.drawString(1.4*inch, y_position, f"Station Code: {station_code}")
                y_position -= 0.25*inch
            
            y_position -= 0.3*inch
    # If status is 'none_nearby', we simply don't show the section at all
    
    # Tram Stop Section (only show if tram system exists in area)
    tram_data = data.get('tram_stop', {})
    
    if tram_data.get('status') == 'success':
        stops = tram_data.get('stops', [])
        
        if stops:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearest Tram/Light Rail Stops")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, stop in enumerate(stops, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = stop.get('name', 'N/A')
                distance = stop.get('distance', 0)
                indicator = stop.get('indicator', 'N/A')
                
                # Convert distance from meters to miles
                distance_miles = round(distance * 0.000621371, 2) if distance else 0
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles ({distance}m)")
                y_position -= 0.18*inch
                if indicator != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Stop Indicator: {indicator}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
    # If status is 'none_nearby', we don't show the section (no tram system in area)
    
    # Bus Stop Section
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(1*inch, y_position, "Nearest Bus Stops")
    y_position -= 0.3*inch
    
    pdf.setFont("Helvetica", 12)
    bus_data = data.get('bus_stop', {})
    
    if bus_data.get('status') == 'success':
        stops = bus_data.get('stops', [])
        
        if stops:
            for i, stop in enumerate(stops, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = stop.get('name', 'N/A')
                distance = stop.get('distance', 0)
                indicator = stop.get('indicator', 'N/A')
                
                # Convert distance from meters to miles
                distance_miles = round(distance * 0.000621371, 2) if distance else 0
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles ({distance}m)")
                y_position -= 0.18*inch
                if indicator != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Stop Indicator: {indicator}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
        else:
            pdf.setFont("Helvetica-Oblique", 11)
            pdf.drawString(1.2*inch, y_position, "No bus stops found nearby")
            pdf.setFont("Helvetica", 12)
    elif bus_data.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Bus stop data unavailable: {bus_data.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Bus stop data unavailable")
        pdf.setFont("Helvetica", 12)
    
    y_position -= 0.5*inch
    
    # Check if we need a new page
    if y_position < 3*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    # ===== SCHOOLS SECTION =====
    schools_data = data.get('schools', {})
    
    if schools_data.get('status') == 'success':
        schools = schools_data.get('schools', [])
        
        if schools:
            y_position = draw_section_header(pdf, 1*inch, y_position, "Education")
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1*inch, y_position, "(Within 10 miles - Data from OpenStreetMap)")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, school in enumerate(schools, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = school.get('name', 'N/A')
                distance_miles = school.get('distance_miles', 0)
                address = school.get('address', 'N/A')
                town = school.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
        else:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearby Schools")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica-Oblique", 11)
            pdf.drawString(1.2*inch, y_position, "No schools found within 15 miles")
            pdf.setFont("Helvetica", 12)
            y_position -= 0.5*inch
    
    elif schools_data.get('status') == 'error':
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(1*inch, y_position, "Nearby Schools")
        y_position -= 0.3*inch
        
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"School data unavailable: {schools_data.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
        y_position -= 0.5*inch
    
    # Healthcare Section
    healthcare_data = data.get('healthcare', {})
    
    if healthcare_data.get('status') == 'success':
        gp_surgeries = healthcare_data.get('gp_surgeries', [])
        hospitals = healthcare_data.get('hospitals', [])
        
        # GP Surgeries
        if gp_surgeries:
            # Check if we need a new page
            if y_position < 3*inch:
                pdf.showPage()
                y_position = height - 1*inch
            
            y_position = draw_section_header(pdf, 1*inch, y_position, "Healthcare")
            
            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColor(COLORS['primary'])
            pdf.drawString(1.2*inch, y_position, "GP Surgeries")
            pdf.setFillColor(COLORS['dark_gray'])
            y_position -= 0.2*inch
            
            pdf.setFont("Helvetica-Oblique", 9)
            pdf.setFillColor(COLORS['light_gray'])
            pdf.drawString(1.2*inch, y_position, "(Within 5 miles - Data from OpenStreetMap)")
            pdf.setFillColor(COLORS['dark_gray'])
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, surgery in enumerate(gp_surgeries, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = surgery.get('name', 'N/A')
                distance_miles = surgery.get('distance_miles', 0)
                address = surgery.get('address', 'N/A')
                town = surgery.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
        
        # Hospitals
        if hospitals:
            # Check if we need a new page
            if y_position < 3*inch:
                pdf.showPage()
                y_position = height - 1*inch
            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearest Hospitals")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1*inch, y_position, "(Within 15 miles - Data from OpenStreetMap)")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, hospital in enumerate(hospitals, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = hospital.get('name', 'N/A')
                distance_miles = hospital.get('distance_miles', 0)
                address = hospital.get('address', 'N/A')
                town = hospital.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
        
        # If no healthcare facilities found
        if not gp_surgeries and not hospitals:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Healthcare Facilities")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica-Oblique", 11)
            pdf.drawString(1.2*inch, y_position, "No GP surgeries or hospitals found within 15 miles")
            pdf.setFont("Helvetica", 12)
            y_position -= 0.5*inch
    
    elif healthcare_data.get('status') == 'error':
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(1*inch, y_position, "Healthcare Facilities")
        y_position -= 0.3*inch
        
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Healthcare data unavailable: {healthcare_data.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
        y_position -= 0.5*inch
    
    # Lifestyle Amenities Section
    lifestyle_data = data.get('lifestyle', {})
    
    if lifestyle_data.get('status') == 'success':
        supermarkets = lifestyle_data.get('supermarkets', [])
        cafes = lifestyle_data.get('cafes', [])
        restaurants = lifestyle_data.get('restaurants', [])
        gyms = lifestyle_data.get('gyms', [])
        
        # Check if we have any lifestyle data to show
        if supermarkets or cafes or restaurants or gyms:
            # Check if we need a new page
            if y_position < 3*inch:
                pdf.showPage()
                y_position = height - 1*inch
            
            y_position = draw_section_header(pdf, 1*inch, y_position, "Lifestyle & Amenities")
        
        # Supermarkets
        if supermarkets:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColor(COLORS['primary'])
            pdf.drawString(1.2*inch, y_position, "Supermarkets")
            pdf.setFillColor(COLORS['dark_gray'])
            y_position -= 0.2*inch
            
            pdf.setFont("Helvetica-Oblique", 9)
            pdf.setFillColor(COLORS['light_gray'])
            pdf.drawString(1.2*inch, y_position, "(Within 15 miles - Data from OpenStreetMap)")
            pdf.setFillColor(COLORS['dark_gray'])
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, supermarket in enumerate(supermarkets, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = supermarket.get('name', 'N/A')
                distance_miles = supermarket.get('distance_miles', 0)
                address = supermarket.get('address', 'N/A')
                town = supermarket.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
        
        # Cafes
        if cafes:
            # Check if we need a new page
            if y_position < 3*inch:
                pdf.showPage()
                y_position = height - 1*inch
            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearest Cafes")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1*inch, y_position, "(Within 15 miles - Data from OpenStreetMap)")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, cafe in enumerate(cafes, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = cafe.get('name', 'N/A')
                distance_miles = cafe.get('distance_miles', 0)
                address = cafe.get('address', 'N/A')
                town = cafe.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
        
        # Restaurants
        if restaurants:
            # Check if we need a new page
            if y_position < 3*inch:
                pdf.showPage()
                y_position = height - 1*inch
            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearest Restaurants")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1*inch, y_position, "(Within 15 miles - Data from OpenStreetMap)")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, restaurant in enumerate(restaurants, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = restaurant.get('name', 'N/A')
                distance_miles = restaurant.get('distance_miles', 0)
                address = restaurant.get('address', 'N/A')
                town = restaurant.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
        
        # Gyms/Sports Facilities
        if gyms:
            # Check if we need a new page
            if y_position < 3*inch:
                pdf.showPage()
                y_position = height - 1*inch
            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(1*inch, y_position, "Nearest Gyms & Sports Facilities")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1*inch, y_position, "(Within 15 miles - Data from OpenStreetMap)")
            y_position -= 0.3*inch
            
            pdf.setFont("Helvetica", 12)
            
            for i, gym in enumerate(gyms, 1):
                if y_position < 1.5*inch:
                    pdf.showPage()
                    y_position = height - 1*inch
                
                name = gym.get('name', 'N/A')
                distance_miles = gym.get('distance_miles', 0)
                address = gym.get('address', 'N/A')
                town = gym.get('town', 'N/A')
                
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(1.2*inch, y_position, f"{i}. {name}")
                y_position -= 0.2*inch
                
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.4*inch, y_position, f"Distance: {distance_miles} miles")
                y_position -= 0.18*inch
                if town != 'N/A':
                    pdf.drawString(1.4*inch, y_position, f"Town: {town}")
                    y_position -= 0.18*inch
                if address != 'Address not available':
                    pdf.drawString(1.4*inch, y_position, f"Address: {address}")
                    y_position -= 0.18*inch
                y_position -= 0.07*inch
            
            y_position -= 0.3*inch
    
    elif lifestyle_data.get('status') == 'error':
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(1*inch, y_position, "Lifestyle Amenities")
        y_position -= 0.3*inch
        
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Lifestyle amenities data unavailable: {lifestyle_data.get('error_message', 'Unknown error')}")
        pdf.setFont("Helvetica", 12)
        y_position -= 0.5*inch
    
    # Heritage & Planning Restrictions Section
    if y_position < 4*inch:
        pdf.showPage()
        y_position = height - 1*inch
    
    y_position = draw_section_header(pdf, 1*inch, y_position, "Heritage & Planning Restrictions")
    
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(COLORS['light_gray'])
    pdf.drawString(1*inch, y_position, "(Data from Historic England)")
    pdf.setFillColor(COLORS['dark_gray'])
    y_position -= 0.25*inch
    
    # Listed Building Status
    listed_building = data.get('listed_building', {})
    
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(1.2*inch, y_position, "Listed Building Status")
    y_position -= 0.25*inch
    
    pdf.setFont("Helvetica", 12)
    
    if listed_building.get('status') == 'success':
        if listed_building.get('is_listed'):
            # Property IS listed
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(1.4*inch, y_position, f"Status: Listed Building - Grade {listed_building.get('grade', 'Unknown')} [!]")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica", 11)
            pdf.drawString(1.4*inch, y_position, f"Building Name: {listed_building.get('name', 'N/A')}")
            y_position -= 0.2*inch
            
            date_listed = listed_building.get('date_listed', 'Unknown')
            pdf.drawString(1.4*inch, y_position, f"Date Listed: {date_listed}")
            y_position -= 0.2*inch
            
            list_entry = listed_building.get('list_entry', 'N/A')
            pdf.drawString(1.4*inch, y_position, f"List Entry Number: {list_entry}")
            y_position -= 0.3*inch
            
            # Warning text
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(1.4*inch, y_position, "Important:")
            y_position -= 0.18*inch
            
            pdf.setFont("Helvetica", 9)
            pdf.drawString(1.4*inch, y_position, "\u2022 Listed building consent required for any alterations, extensions, or demolition")
            y_position -= 0.15*inch
            pdf.drawString(1.4*inch, y_position, "\u2022 Protection applies to the entire building, inside and out")
            y_position -= 0.15*inch
            pdf.drawString(1.4*inch, y_position, "\u2022 Consult local planning authority before any work")
            y_position -= 0.3*inch
        else:
            # Property is NOT listed
            pdf.setFont("Helvetica", 12)
            pdf.drawString(1.4*inch, y_position, "Status: Not a Listed Building [OK]")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1.4*inch, y_position, "This property is not designated as a listed building.")
            y_position -= 0.3*inch
    elif listed_building.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.4*inch, y_position, f"Listed building data unavailable: {listed_building.get('error_message', 'Unknown error')}")
        y_position -= 0.3*inch
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.4*inch, y_position, "Listed building data unavailable")
        y_position -= 0.3*inch
    
    # Conservation Area Status
    conservation_area = data.get('conservation_area', {})
    
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(1.2*inch, y_position, "Conservation Area Status")
    y_position -= 0.25*inch
    
    pdf.setFont("Helvetica", 12)
    
    if conservation_area.get('status') == 'success':
        if conservation_area.get('in_conservation_area'):
            # Property IS in a conservation area
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(1.4*inch, y_position, "Status: Within Conservation Area [!]")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica", 11)
            area_name = conservation_area.get('area_name', 'N/A')
            pdf.drawString(1.4*inch, y_position, f"Conservation Area: {area_name}")
            y_position -= 0.2*inch
            
            local_auth = conservation_area.get('local_authority', 'N/A')
            pdf.drawString(1.4*inch, y_position, f"Local Authority: {local_auth}")
            y_position -= 0.2*inch
            
            date_desig = conservation_area.get('date_designated', 'Unknown')
            pdf.drawString(1.4*inch, y_position, f"Designated: {date_desig}")
            y_position -= 0.3*inch
            
            # Warning text
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(1.4*inch, y_position, "Important:")
            y_position -= 0.18*inch
            
            pdf.setFont("Helvetica", 9)
            pdf.drawString(1.4*inch, y_position, "\u2022 Additional planning restrictions apply")
            y_position -= 0.15*inch
            pdf.drawString(1.4*inch, y_position, "\u2022 Special consent may be needed for alterations or extensions")
            y_position -= 0.15*inch
            pdf.drawString(1.4*inch, y_position, "\u2022 Demolition restrictions may apply")
            y_position -= 0.15*inch
            pdf.drawString(1.4*inch, y_position, "\u2022 Tree work may require special permission")
            y_position -= 0.3*inch
        else:
            # Property is NOT in a conservation area
            pdf.setFont("Helvetica", 12)
            pdf.drawString(1.4*inch, y_position, "Status: Not in a Conservation Area [OK]")
            y_position -= 0.25*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1.4*inch, y_position, "This property is not located within a conservation area.")
            y_position -= 0.3*inch
    elif conservation_area.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.4*inch, y_position, f"Conservation area data unavailable: {conservation_area.get('error_message', 'Unknown error')}")
        y_position -= 0.3*inch
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.4*inch, y_position, "Conservation area data unavailable")
        y_position -= 0.3*inch
    
    # Additional information
    if (listed_building.get('status') == 'success' and listed_building.get('is_listed')) or \
       (conservation_area.get('status') == 'success' and conservation_area.get('in_conservation_area')):
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(1.2*inch, y_position, "For More Information:")
        y_position -= 0.2*inch
        
        pdf.setFont("Helvetica", 9)
        pdf.drawString(1.4*inch, y_position, "Visit: https://historicengland.org.uk/listing/the-list/")
        y_position -= 0.15*inch
        pdf.drawString(1.4*inch, y_position, "Contact your local planning authority for guidance on restrictions")
        y_position -= 0.5*inch
    
    # Land Registry Price Paid Data
    price_paid = data.get('price_paid', {})
    
    # Check if we need a new page
    if y_position < 3*inch:
        pdf.showPage()
        y_position = 10*inch
    
    y_position = draw_section_header(pdf, 1*inch, y_position, "Property Sale History")
    
    if price_paid.get('status') == 'success':
        if price_paid.get('property_found') and price_paid.get('transactions'):
            transactions = price_paid.get('transactions', [])
            most_recent = transactions[0] if transactions else None
            
            if most_recent:
                # Most recent sale
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawString(1.2*inch, y_position, "Most Recent Sale")
                y_position -= 0.25*inch
                
                pdf.setFont("Helvetica", 11)
                sale_price = most_recent.get('price', 0)
                pdf.drawString(1.4*inch, y_position, f"Sale Price: £{sale_price:,}")
                y_position -= 0.2*inch
                
                sale_date = most_recent.get('date', 'Unknown')
                pdf.drawString(1.4*inch, y_position, f"Sale Date: {sale_date}")
                y_position -= 0.2*inch
                
                property_type = most_recent.get('property_type', 'Unknown')
                pdf.drawString(1.4*inch, y_position, f"Property Type: {property_type}")
                y_position -= 0.2*inch
                
                tenure = most_recent.get('tenure', 'Unknown')
                pdf.drawString(1.4*inch, y_position, f"Tenure: {tenure}")
                y_position -= 0.2*inch
                
                new_build = most_recent.get('new_build', False)
                new_build_text = "Yes" if new_build else "No"
                pdf.drawString(1.4*inch, y_position, f"New Build: {new_build_text}")
                y_position -= 0.3*inch
                
                # If multiple sales, show count
                if len(transactions) > 1:
                    pdf.setFont("Helvetica-Oblique", 10)
                    pdf.drawString(1.4*inch, y_position, f"This property has {len(transactions)} recorded sale(s) since 1995")
                    y_position -= 0.25*inch
                    
                    # Show all sales
                    pdf.setFont("Helvetica-Bold", 11)
                    pdf.drawString(1.4*inch, y_position, "Complete Sale History:")
                    y_position -= 0.2*inch
                    
                    pdf.setFont("Helvetica", 9)
                    for i, transaction in enumerate(transactions, 1):
                        t_price = transaction.get('price', 0)
                        t_date = transaction.get('date', 'Unknown')
                        pdf.drawString(1.6*inch, y_position, f"{i}. £{t_price:,} - {t_date}")
                        y_position -= 0.15*inch
                    
                    y_position -= 0.15*inch
        else:
            # No transactions found for this property
            pdf.setFont("Helvetica", 11)
            pdf.drawString(1.2*inch, y_position, "No recorded sales found for this property since 1995")
            y_position -= 0.2*inch
            
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(1.2*inch, y_position, "Note: Only sales registered with HM Land Registry are shown")
            y_position -= 0.3*inch
    elif price_paid.get('status') == 'error':
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, f"Sale history unavailable: {price_paid.get('error_message', 'Unknown error')}")
        y_position -= 0.3*inch
    else:
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(1.2*inch, y_position, "Sale history unavailable")
        y_position -= 0.3*inch
    
    # Data attribution
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(1.2*inch, y_position, "Contains HM Land Registry data © Crown copyright and database right 2026")
    y_position -= 0.5*inch
    
    # Footer
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(1*inch, 0.75*inch, "Generated by Flask PDF Generator")
    pdf.drawString(1*inch, 0.5*inch, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Finalize PDF
    pdf.save()
    
    # Move buffer position to beginning
    buffer.seek(0)
    return buffer


    
    # Finalize PDF
    pdf.save()
    
    # Move buffer position to beginning
    buffer.seek(0)
    return buffer
