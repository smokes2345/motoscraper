# modem_scraper/scrape_modem.py
import argparse
import requests
from bs4 import BeautifulSoup
from prometheus_client import make_wsgi_app, Gauge, Counter, Histogram
from wsgiref.simple_server import make_server
import time

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('url', help='URL to scrape', default='http://192.168.100.1/MotoConnection.asp')
args = parser.parse_args()

# Prometheus metrics
pwr_metric = Gauge('moto_pwr', 'Power for downstream bonded channels', ['modulation', 'channel_id', 'freq'])
snr_metric = Gauge('moto_snr', 'SNR for downstream bonded channels', ['modulation', 'channel_id', 'freq'])
corrected_metric = Gauge('moto_corrected', 'Corrected power for downstream bonded channels', ['modulation', 'channel_id', 'freq'])
uncorrected_metric = Gauge('moto_uncorrected', 'Uncorrected power for downstream bonded channels', ['modulation', 'channel_id', 'freq'])

def fetch_connection_data(url):
    """Fetch and parse connection data from the web page"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the correct table
        table = None
        for table_candidate in soup.find_all('table'):
            # Check if the table contains the header text
            rows = table_candidate.find_all('tr')
            for row in rows:
                if row.find('td') and row.find('td').text.strip() == 'Downstream Bonded Channels':
                    table = table_candidate
                    break
            if table:
                break
        
        if not table:
            print("Could not find the correct table in the HTML")
            return
        
        # Extract rows
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip the header row
            # Skip the "Total" row
            if row.find('td') and \
               (row.find('td').text.strip() == 'Total' or \
                row.find('td').text.strip() == 'Channel'):
                continue
            
            cols = row.find_all('td')
            if len(cols) >= 9:
                modulation = cols[2].text.strip()
                channel_id = cols[3].text.strip()
                freq = cols[4].text.strip()
                pwr = cols[5].text.strip()
                snr = cols[6].text.strip()
                corrected = cols[7].text.strip()
                uncorrected = cols[8].text.strip()
                
                # Add to histograms
                try:
                    pwr_metric.labels(modulation=modulation, channel_id=channel_id, freq=freq).set(float(pwr))
                    snr_metric.labels(modulation=modulation, channel_id=channel_id, freq=freq).set(float(snr))
                    corrected_metric.labels(modulation=modulation, channel_id=channel_id, freq=freq).set(float(corrected))
                    uncorrected_metric.labels(modulation=modulation, channel_id=channel_id, freq=freq).set(float(uncorrected))
                    print(f"Found {modulation} {channel_id} {freq}: PWR={pwr}, SNR={snr}, Corrected={corrected}, Uncorrected={uncorrected}")
                except Exception as e:
                    print(f"Error observing metric: {e}")
                    continue
                
    except requests.RequestException as e:
        print(f"Error fetching data: {str(e)}")
    except Exception as e:
        print(f"Error processing data: {str(e)}")

def custom_wsgi_app(environ, start_response):
    """Custom WSGI app that triggers data fetching when /metrics is accessed"""
    if environ['PATH_INFO'] == '/metrics':
        fetch_connection_data(args.url)
    return make_wsgi_app()(environ, start_response)

if __name__ == '__main__':
    # Start the custom WSGI server
    server = make_server('', 8000, custom_wsgi_app)
    print("Server running on http://localhost:8000")
    server.serve_forever()