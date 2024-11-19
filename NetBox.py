import config

from OdooAPI import get_inventory_by_brand

netbox_url = config.URL_NETBOX
token = config.TOKEN
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json",
}

import requests
from config import PRODUCTS

def determine_tag(device_name):
    # Iterate through TAG_RULES to find a matching tag for the device_name
    for tag, keywords in config.TAG_RULES.items():
        # Check if any keyword is present in the device name
        if any(keyword in device_name for keyword in keywords):
            print(f"Fetching tag '{tag}' for device '{device_name}'...")
            response = requests.get(
                f"{netbox_url}/api/dcim/device-roles/",
                headers=headers,
                params={"name": tag}
            )

            if response.status_code == 200:
                tag_id = response.json()["results"][0]["id"]
                print(f"Tag '{tag}' found with ID: {tag_id}")
                return tag_id
            else:
                print(f"Error fetching tag '{tag}': {response.status_code}")
                return None

    # If no match is found, return None or a default tag
    print(f"No tag found for device '{device_name}'.")
    return None


def check_and_add_manufacturer(device_name):
    try:
        # Extract the prefix and remove additional terms before the actual model name
        manufacturer_prefix = next((product for product in PRODUCTS if device_name.startswith(product)), None)

        if manufacturer_prefix:
            # Remove the prefix and any additional terms, keeping only the model name
            model_name = device_name.replace(manufacturer_prefix, "").strip().split(" ", 1)[-1]

            print(f"Checking manufacturer for prefix '{manufacturer_prefix}'...")
            response = requests.get(
                f"{netbox_url}/api/dcim/manufacturers/",
                headers=headers,
                params={"name": manufacturer_prefix}
            )

            if response.status_code == 200:
                results = response.json().get("results", [])

                # If the manufacturer exists, return its ID
                if results:
                    manufacturer_id = results[0]["id"]
                    print(f"Manufacturer '{manufacturer_prefix}' found with ID: {manufacturer_id}")
                    return manufacturer_id, model_name

                # If the manufacturer does not exist, create a new one
                else:
                    print(f"Manufacturer '{manufacturer_prefix}' not found. Creating a new one...")
                    create_response = requests.post(
                        f"{netbox_url}/api/dcim/manufacturers/",
                        headers=headers,
                        json={"name": manufacturer_prefix, "slug": manufacturer_prefix.lower().replace(" ", "-")}
                    )

                    if create_response.status_code == 201:
                        new_manufacturer_id = create_response.json()["id"]
                        print(f"Manufacturer '{manufacturer_prefix}' created with ID: {new_manufacturer_id}")
                        return new_manufacturer_id, model_name
                    else:
                        print(f"Error creating manufacturer: {create_response.status_code}")
                        print("Details:", create_response.text)
                        return None, None
            else:
                print(f"Error checking manufacturer: {response.status_code}")
                print("Details:", response.text)
                return None, None
        else:
            print(f"No valid prefix found in device name: {device_name}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error checking or creating manufacturer: {e}")
        return None, None


def check_and_add_device_type(device_name, manufacturer_id):
    try:
        print(f"Checking if device type '{device_name}' exists...")
        response = requests.get(
            f"{netbox_url}/api/dcim/device-types/",
            headers=headers,
            params={"model": device_name}  # Fixed to search by 'model'
        )

        if response.status_code == 200:
            results = response.json().get("results", [])

            # Check if the device type already exists (case insensitive)
            for device in results:
                if device["model"].lower() == device_name.lower():
                    print(f"Device type '{device_name}' found:", device)
                    return device['id']

            print(f"Device type '{device_name}' not found. Creating a new one...")

            # Data for creating the new device type
            device_data = {
                "manufacturer": manufacturer_id,
                "model": device_name,
                "slug": device_name.lower().replace(" ", "-"),
                "u_height": 2
            }

            creation_response = requests.post(
                f"{netbox_url}/api/dcim/device-types/",
                headers=headers,
                json=device_data,
            )

            if creation_response.status_code == 201:
                created_device = creation_response.json()
                print(f"Device type '{device_name}' created successfully:", created_device)
                return created_device['id']
            else:
                print(f"Error creating device type: {creation_response.status_code}")
                print("Details:", creation_response.text)
                return False
        else:
            print(f"Error checking device types: {response.status_code}")
            print("Details:", response.text)
            return False

    except requests.exceptions.RequestException as e:
        print(f"Connection error to NetBox: {e}")
        return False


def add_devices_if_they_are_not_in_already(device_name, id_device_model, device_id, tag_id, serial_number):
    try:
        print(f"Checking if device with serial '{serial_number}' exists...")
        response = requests.get(
            f"{netbox_url}/api/dcim/devices/",
            headers=headers,
            params={"serial": serial_number}
        )

        if response.status_code == 200:
            response_data = response.json()

            if response_data.get("count", 0) == 0 or not response_data.get("results"):
                print("Device not found. Creating a new device...")
                device_data = {
                    "name": device_name,
                    "device_type": device_id,
                    "manufacturer": id_device_model,
                    "site": 1,
                    "status": "active",
                    "role": tag_id
                }

                creation_response = requests.post(
                    f"{netbox_url}/api/dcim/devices/",
                    headers=headers,
                    json=device_data
                )

                if creation_response.status_code == 201:
                    print("Device created successfully:", creation_response.json())
                else:
                    print(f"Error creating device: {creation_response.status_code}")
                    print("Details:", creation_response.text)
            else:
                print("Device already exists in the system.")
        else:
            print(f"Error checking device: {response.status_code}")
            print("Details:", response.text)

    except requests.exceptions.RequestException as req_err:
        print("Communication error with NetBox:", req_err)

    except Exception as e:
        print("Unexpected error:", e)


inventory = get_inventory_by_brand()

for brand, items in inventory.items():
    print(f"\nProcessing products for brand '{brand}':")
    for item in items:
        id_device_model, model_name = check_and_add_manufacturer(item['Product Name'])
        tag_id = determine_tag(item['Product Name'])
        device_id = check_and_add_device_type(model_name, id_device_model)
        add_devices_if_they_are_not_in_already(
            item['Device Name'],
            id_device_model,
            device_id,
            tag_id,
            item['Serial Number']
        )
