from flask import Flask, render_template, request, send_file, jsonify
from datetime import datetime
import re
import requests

from config import EASYPOSTCODES_API_KEY
from api_functions import fetch_all_data
from pdf_generator import create_pdf

app = Flask(__name__)


@app.route('/')
def index():
    """Render the main form page"""
    return render_template('index.html')


@app.route('/search-addresses', methods=['POST'])
def search_addresses():
    """
    Search for addresses using easypostcodes.com API
    """
    try:
        data = request.get_json()
        postcode = data.get('postcode', '').strip()

        print(f"=== ADDRESS SEARCH DEBUG ===")
        print(f"Received postcode (original): {postcode}")

        if not postcode:
            return jsonify({'error': 'Postcode is required'}), 400

        # Check if API key is configured
        if EASYPOSTCODES_API_KEY == 'your-api-key-here':
            return jsonify({'error': 'API key not configured. Please add your easypostcodes.com API key.'}), 500

        # Format postcode - remove spaces, uppercase
        postcode_clean = postcode.replace(' ', '').upper()

        print(f"Cleaned postcode (no spaces): {postcode_clean}")

        # Call easypostcodes.com API
        url = f'https://api.easypostcodes.com/addresses/{postcode_clean}'
        headers = {
            'Key': EASYPOSTCODES_API_KEY
        }

        print(f"Calling URL: {url}")
        print(f"With header Key: {EASYPOSTCODES_API_KEY[:10]}...")

        response = requests.get(url, headers=headers, timeout=10)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text[:500]}")

        if response.status_code == 200:
            api_data = response.json()
            print(f"SUCCESS! API Response is list: {isinstance(api_data, list)}")

            # easypostcodes returns a list of address objects
            addresses = api_data if isinstance(api_data, list) else []
            print(f"Number of addresses found: {len(addresses)}")

            # Format addresses using the envelopeAddress.summaryLine for clean display
            formatted_addresses = []
            for addr in addresses:
                # Use the pre-formatted summaryLine from envelopeAddress
                if addr.get('envelopeAddress') and addr['envelopeAddress'].get('summaryLine'):
                    formatted = addr['envelopeAddress']['summaryLine']
                else:
                    # Fallback: build from individual fields
                    parts = []
                    if addr.get('subBuildingName'):
                        parts.append(addr['subBuildingName'])
                    if addr.get('buildingNumber'):
                        parts.append(addr['buildingNumber'])
                    if addr.get('thoroughfareAndDescriptor'):
                        parts.append(addr['thoroughfareAndDescriptor'])
                    if addr.get('postTown'):
                        parts.append(addr['postTown'])
                    if addr.get('postCode'):
                        parts.append(addr['postCode'])
                    formatted = ', '.join(parts)

                formatted_addresses.append(formatted)

                if len(formatted_addresses) <= 3:  # Only print first 3
                    print(f"Formatted address: {formatted}")

            return jsonify({
                'addresses': formatted_addresses,
                'count': len(formatted_addresses)
            })
        elif response.status_code == 404:
            print(f"404 Error - Postcode not found in database")
            return jsonify({'error': 'No addresses found for this postcode.'}), 404
        elif response.status_code == 401:
            print(f"401 Error - Invalid API key")
            return jsonify({'error': 'Invalid API key. Please check your easypostcodes.com API key.'}), 401
        elif response.status_code == 403:
            print(f"403 Error - Forbidden")
            return jsonify({'error': 'Access forbidden. Please check your API key permissions.'}), 403
        elif response.status_code == 429:
            print(f"429 Error - Rate limit exceeded")
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        elif response.status_code == 400:
            print(f"400 Error - Bad request")
            return jsonify({'error': 'Invalid postcode format'}), 400
        else:
            print(f"Unexpected status code: {response.status_code}")
            return jsonify({'error': f'API error: {response.status_code}'}), 500

    except requests.exceptions.Timeout:
        print(f"Request timeout")
        return jsonify({'error': 'Request timed out. Please try again.'}), 500
    except requests.exceptions.RequestException as e:
        print(f"Error calling easypostcodes.com: {e}")
        return jsonify({'error': 'Failed to connect to address service'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred'}), 500


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Handle form submission and generate PDF
    """
    # Get form data
    first_name = request.form.get('firstName', '').strip()
    last_name = request.form.get('lastName', '').strip()
    postcode = request.form.get('postcode', '').strip().upper()
    address = request.form.get('address', '').strip()

    # Validate postcode server-side
    if not validate_postcode(postcode):
        return "Invalid postcode", 400

    # Validate address is selected
    if not address:
        return "Please select an address", 400

    # Format postcode with space if needed
    postcode = format_postcode(postcode)

    # Fetch data from all APIs (pass address for matching)
    api_data = fetch_all_data(postcode, address)

    # Generate PDF
    pdf_buffer = create_pdf(first_name, last_name, postcode, address, api_data)

    # Return PDF file for download
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'report_{postcode.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )


def validate_postcode(postcode):
    """
    Validate UK postcode format
    Returns True if valid, False otherwise
    """
    # UK postcode regex pattern
    pattern = r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$'
    return bool(re.match(pattern, postcode, re.IGNORECASE))


def format_postcode(postcode):
    """
    Format postcode with proper spacing
    """
    # Remove any existing spaces
    postcode = postcode.replace(' ', '')
    # Add space before last 3 characters
    if len(postcode) >= 5:
        return postcode[:-3] + ' ' + postcode[-3:]
    return postcode


if __name__ == '__main__':
    app.run(debug=True)