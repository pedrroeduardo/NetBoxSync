# URL for the ERP system endpoint
URL_ERP = 'https://erp.ict-tfbern.ch'

# URL for the NetBox system endpoint
URL_NETBOX = 'http://netbox.ict-tfbern.ch'

# Database name to connect to
DATABASE = ''

# Username for authentication with the ERP API
USERNAME = ''

# Password associated with the API user
PASSWORD = ''

# Token for API access authorization
TOKEN = ''

# List of product keywords to be searched and grouped
PRODUCTS = ["Cisco", "Netgate"]

TAG_RULES = {
    "Access Point": ["Cisco AP", "Access Point"],
    "Firewall": ["Netgate", "Firewall"],
    "Switch": ["Cisco"]
}

# List of location codes where products should be searched
LOCATIONS = ["LA", "LH3", "LA3", "LA9", "Cus"]


