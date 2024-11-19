import xmlrpc.client
import config

url = config.URL_ERP
db = config.DATABASE
username = config.USERNAME
password = config.PASSWORD


def authenticate():
    try:
        print("Authenticating user...")
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
        user_id = common.authenticate(db, username, password, {})
        if not user_id:
            print("Authentication failed. Please check credentials.")
            return None
        print(f"Authentication successful. User ID: {user_id}")
        return user_id
    except Exception as e:
        print("Authentication error:", e)
        return None


def get_serial_info(db, user, password, serial_id):
    try:
        print(f"Fetching details for serial ID: {serial_id}")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
        serial_details = models.execute_kw(
            db, user, password,
            'stock.lot', 'search_read',
            [[['id', '=', serial_id]]],
            {'fields': ['id', 'name', 'lot_properties']}
        )

        if serial_details:
            print(f"Serial details found for ID {serial_id}.")
            serial = serial_details[0]
            serial_name = serial.get('name')
            switch_name_value = None
            for prop in serial.get('lot_properties', []):
                if prop.get('string') == 'Device Name':
                    switch_name_value = prop.get('value')
                    break
            return serial.get('id'), serial_name, switch_name_value
        else:
            print(f"No details found for serial ID: {serial_id}")
    except xmlrpc.client.Fault as e:
        print("XML-RPC specific error while fetching serial info:", e)
    except Exception as e:
        print("Error while fetching serial info:", e)
    return None, None, None


def get_filtered_product_inventory(url, db, user, password):
    try:
        print("Fetching products filtered by brand (Cisco or Netgate)...")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
        product_details = models.execute_kw(
            db, user, password,
            'product.product', 'search_read',
            [['|', ['name', 'ilike', 'Cisco'], ['display_name', 'ilike', 'Cisco'], '|', ['name', 'ilike', 'Netgate'],
              ['display_name', 'ilike', 'Netgate']]],
            {'fields': ['id', 'name', 'default_code']}
        )

        if not product_details:
            print("No products found with 'Cisco' or 'Netgate' in the name.")
            return []

        print(f"Found {len(product_details)} products matching the filter.")
        filtered_products = [product for product in product_details if any(
            prod.lower() in product.get('name', '').lower() for prod in config.PRODUCTS)]

        product_ids = list(set([product['id'] for product in filtered_products]))
        print(f"{len(product_ids)} products matched after applying additional filters.")
        return product_ids
    except Exception as e:
        print("Error while fetching filtered product inventory:", e)
        return []


def get_inventory_by_brand():
    print("Starting inventory retrieval by brand...")
    user = authenticate()
    if user is None:
        print("Authentication failed. Unable to proceed.")
    else:
        try:
            print("Fetching product IDs based on filters...")
            product_ids = get_filtered_product_inventory(url, db, user, password)
            if not product_ids:
                print("No matching products found. Exiting.")
            else:
                print(f"Processing inventory for {len(product_ids)} products...")
                models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

                # Initialize the inventory dictionary
                inventory_data = {key: [] for key in config.PRODUCTS}

                processed_serial_ids = set()

                for product_id in product_ids:
                    print(f"Fetching stock quantities for product ID: {product_id}")
                    stock_quants = models.execute_kw(
                        db, user, password,
                        'stock.quant', 'search_read',
                        [[['product_id', '=', product_id]]],
                        {'fields': ['id', 'product_id', 'location_id', 'lot_id']}
                    )

                    for quant in stock_quants:
                        location_name = quant["location_id"][1]

                        if any(loc in location_name for loc in config.LOCATIONS):
                            serial_id = quant["lot_id"][0]
                            if serial_id not in processed_serial_ids:
                                print(f"Processing serial ID: {serial_id}")
                                processed_serial_ids.add(serial_id)
                                product_id_internal = quant['id']
                                product_name = quant['product_id'][1]
                                serial_info = get_serial_info(db, user, password, serial_id)
                                serial_number = serial_info[1]
                                switch_name = serial_info[2]

                                # Determine the brand key based on product name
                                brand_key = next((brand for brand in config.PRODUCTS if brand in product_name), None)
                                if brand_key:
                                    print(f"Adding product {product_name} under brand {brand_key}.")
                                    inventory_data[brand_key].append({
                                        "Product ID": product_id_internal,
                                        "Product Name": product_name,
                                        "Location": location_name,
                                        "Serial Number": serial_number,
                                        "Device Name": switch_name
                                    })

                print("Inventory retrieval completed.")
                return inventory_data
        except Exception as e:
            print("Error while fetching product data:", e)
            return None
