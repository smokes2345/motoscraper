modem_scraper/scrape_modem.py
# modem_scraper/main.py
import requests
from bs4 import BeautifulSoup
from prometheus_client import make_wsgi_app, Histogram, Counter, Gauge
from wsgiref.simple_server import make_server
import time
import argparse

# Prometheus metrics
pwr_metric = Gauge('moto_pwr', 'Power for downstream bonded channels', ['modulation', 'channel_id', 'freq'])
snr_metric = Gauge('moto_snr', 'SNR for downstream bonded channels', ['modulation', 'channel_id', 'freq'])
corrected_metric = Gauge('moto_corrected', 'Corrected power for downstream bonded channels', ['modulation', 'channel_id', 'freq'])
uncorrected_metric = Gauge('moto_uncorrected', 'Uncorrected power for downstream bonded channels', ['modulation', 'channel_id', 'freq'])

# Upstream metrics
upstream_symb_rate_metric = Gauge('moto_upstream_symb_rate', 'Symb. Rate for upstream bonded channels', ['channel_type', 'channel_id', 'freq'])
upstream_pwr_metric = Gauge('moto_upstream_pwr', 'Power for upstream bonded channels', ['channel_type', 'channel_id', 'freq'])

# Global variable to store the URL
URL = "http://192.168.100.1/MotoConnection.asp"

def fetch_connection_data(url):
    """Fetch and parse connection data from the web page"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find downstream table
        downstream_table = None
        for table_candidate in soup.find_all('table'):
            # Check if the table contains the header text
            rows = table_candidate.find_all('tr')
            for row in rows:
                if row.find('td') and row.find('td').text.strip() == 'Downstream Bonded Channels':
                    downstream_table = table_candidate
                    break
            if downstream_table:
                break

        if not downstream_table:
            print("Could not find the correct table in the HTML")
            return

        # Extract downstream rows
        downstream_rows = downstream_table.find_all('tr')
        for row in downstream_rows[1:]:  # Skip the header row
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

        # Find upstream table
        upstream_table = None
        for table_candidate in soup.find_all('table'):
            # Check if the table contains the header text
            rows = table_candidate.find_all('tr')
            for row in rows:
                if row.find('td') and row.find('td').text.strip() == 'Upstream Bonded Channels':
                    upstream_table = table_candidate
                    break
            if upstream_table:
                break

        if upstream_table:
            # Extract upstream rows
            upstream_rows = upstream_table.find_all('tr')
            for row in upstream_rows[1:]:  # Skip the header row

                if row.find('td') and \
                    (row.find('td').text.strip() == 'Total' or \
                    row.find('td').text.strip() == 'Channel'):
                    continue

                cols = row.find_all('td')
                if len(cols) >= 7:
                    channel = cols[0].text.strip()
                    lock_status = cols[1].text.strip()
                    channel_type = cols[2].text.strip()
                    channel_id = cols[3].text.strip()
                    freq = cols[4].text.strip()
                    symb_rate = cols[5].text.strip()
                    pwr = cols[6].text.strip()

                    # Add to upstream metrics
                    try:
                        upstream_symb_rate_metric.labels(channel_type=channel_type, channel_id=channel_id, freq=freq).set(float(symb_rate))
                        upstream_pwr_metric.labels(channel_type=channel_type, channel_id=channel_id, freq=freq).set(float(pwr))
                        print(f"Found Upstream Channel {channel_id}: Symb Rate={symb_rate}, PWR={pwr}")
                    except Exception as e:
                        print(f"Error observing upstream metric: {e}")
                        continue

    except requests.RequestException as e:
        print(f"Error fetching data: {str(e)}")
    except Exception as e:
        print(f"Error processing data: {str(e)}")


def custom_wsgi_app(environ, start_response):
    """Custom WSGI app that triggers data fetching when /metrics is accessed"""
    if environ['PATH_INFO'] == '/metrics':
        fetch_connection_data(URL)
    return make_wsgi_app()(environ, start_response)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL to fetch data from', default="http://192.168.100.1/MotoConnection.asp")
    args = parser.parse_args()
    URL = args.url  # Update the global URL

    server = make_server('', 8000, custom_wsgi_app)
    print("Server running on http://localhost:8000")
    server.serve_forever()