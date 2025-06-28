
from utils import PortalMigrator
import requests
# Replace with your Azure service details
SUBSCRIPTION_ID = "a950f946-d138-4c5e-abca-0f5b18544949"
RESOURCE_GROUP_NAME = "rg-apim-dev-portal-1-9vxbht"
SERVICE_NAME = "apim-dev-portal-1-9vxbht"
SNAPSHOT_FOLDER = "./snapshot"

def main():
    migrator = PortalMigrator(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME, SERVICE_NAME, SNAPSHOT_FOLDER)
    migrator.export_portal()

if __name__ == "__main__":
    main()
