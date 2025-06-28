
import os
import json
import requests
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerClient

API_VERSION = "2021-08-01"
MANAGEMENT_API_ENDPOINT = "management.azure.com"

class AzureHttpClient:
    def __init__(self, subscription_id, resource_group_name, service_name):
        self.subscription_id = subscription_id
        self.resource_group_name = resource_group_name
        self.service_name = service_name
        self.credential = DefaultAzureCredential()
        self.access_token = self.get_access_token()
        self.base_url = f"https://{MANAGEMENT_API_ENDPOINT}/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.ApiManagement/service/{self.service_name}"

    def get_access_token(self):
        token = self.credential.get_token("https://management.azure.com/.default")
        return f"Bearer {token.token}"

    def send_request(self, method, url, body=None):
        if not url.startswith("https://"):
            url = self.base_url + url
        
        headers = {
            "If-Match": "*",
            "Content-Type": "application/json",
            "Authorization": self.access_token
        }

        params = {"api-version": API_VERSION}

        response = requests.request(method, url, headers=headers, params=params, json=body)

        if response.status_code in [200, 201, 202]:
            return response.json() if response.text else ""
        else:
            response.raise_for_status()

class PortalMigrator:
    def __init__(self, subscription_id, resource_group_name, service_name, snapshot_folder="./snapshot"):
        self.http_client = AzureHttpClient(subscription_id, resource_group_name, service_name)
        self.snapshot_folder = snapshot_folder

    def list_files_in_directory(self, dir):
        results = []
        for root, _, files in os.walk(dir):
            for file in files:
                if not file.endswith(".info"):
                    results.append(os.path.join(root, file))
        return results

    def get_content_types(self):
        data = self.http_client.send_request("GET", "/contentTypes")
        return [item["id"].split("/")[-1] for item in data["value"]]

    def get_content_items(self, content_type):
        content_items = []
        next_page_url = f"/contentTypes/{content_type}/contentItems"
        while next_page_url:
            data = self.http_client.send_request("GET", next_page_url)
            content_items.extend(data["value"])
            next_page_url = data.get("nextLink")
        return content_items

    def get_content_item(self, content_type, content_item):
        url = f"/contentTypes/{content_type}/contentItems/{content_item}"
        return self.http_client.send_request("GET", url)

    def update_content_item(self, content_type, content_item, body):
        url = f"/contentTypes/{content_type}/contentItems/{content_item}"
        return self.http_client.send_request("PUT", url, body)

    def get_storage_sas_url(self):
        response = self.http_client.send_request("POST", "/portalconfigs/default/listMediaContentSecrets")
        return response["containerSasUrl"]

    def download_blobs(self):
        snapshot_media_folder = os.path.join(self.snapshot_folder, "media")
        os.makedirs(snapshot_media_folder, exist_ok=True)
        
        blob_storage_url = self.get_storage_sas_url()
        container_client = ContainerClient.from_container_url(blob_storage_url)

        for blob in container_client.list_blobs():
            blob_client = container_client.get_blob_client(blob.name)
            download_file_path = os.path.join(snapshot_media_folder, blob.name)
            os.makedirs(os.path.dirname(download_file_path), exist_ok=True)
            with open(download_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())

    def upload_blobs(self):
        snapshot_media_folder = os.path.join(self.snapshot_folder, "media")
        if not os.path.exists(snapshot_media_folder):
            print("No media files found, skipping upload.")
            return

        blob_storage_url = self.get_storage_sas_url()
        container_client = ContainerClient.from_container_url(blob_storage_url)
        
        for file_path in self.list_files_in_directory(snapshot_media_folder):
            blob_name = os.path.relpath(file_path, snapshot_media_folder)
            with open(file_path, "rb") as data:
                container_client.upload_blob(name=blob_name, data=data, overwrite=True)

    def capture_content(self):
        result = {}
        content_types = self.get_content_types()
        for content_type in content_types:
            content_items = self.get_content_items(content_type)
            for item in content_items:
                result[item["id"]] = item
                del item["id"]
        
        os.makedirs(self.snapshot_folder, exist_ok=True)
        with open(os.path.join(self.snapshot_folder, "data.json"), "w") as f:
            json.dump(result, f, indent=4)

    def generate_content(self):
        snapshot_file_path = os.path.join(self.snapshot_folder, "data.json")
        with open(snapshot_file_path, "r") as f:
            data = json.load(f)
        
        for key, value in data.items():
            self.http_client.send_request("PUT", key, value)

    def export_portal(self):
        print("Exporting portal...")
        self.capture_content()
        self.download_blobs()
        print("Export complete.")

    def import_portal(self):
        print("Importing portal...")
        self.generate_content()
        self.upload_blobs()
        print("Import complete.")

