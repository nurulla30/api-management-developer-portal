
import argparse
import os
from dotenv import load_dotenv

from utils import PortalMigrator
import requests

def main():
    parser = argparse.ArgumentParser(description='Capture developer portal content from an API Management instance.')
    parser.add_argument('--folder', type=str, help='The folder to save the captured data.', required=True)
    parser.add_argument('--env-file', type=str, help='Path to the environment file.', required=True)
    
    args = parser.parse_args()

    load_dotenv(dotenv_path=args.env_file) # Load environment variables from specified .env file

    subscription_id = os.getenv("SUBSCRIPTION_ID")
    resource_group_name = os.getenv("RESOURCE_GROUP_NAME")
    service_name = os.getenv("SERVICE_NAME")

    if not all([subscription_id, resource_group_name, service_name]):
        raise ValueError("Environment variables SUBSCRIPTION_ID, RESOURCE_GROUP_NAME, and SERVICE_NAME must be set in the provided .env file.")

    migrator = PortalMigrator(subscription_id, resource_group_name, service_name, args.folder)
    migrator.export_portal()

if __name__ == "__main__":
    main()
