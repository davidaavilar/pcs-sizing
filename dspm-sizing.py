import requests, json, os, time, csv, datetime, logging, sys, math, argparse
from datetime import date
from datetime import timedelta
from csv import QUOTE_ALL

logformat = "%(asctime)s - %(message)s"
datefmt = "%m-%d %H:%M:%S"
logging.basicConfig(filename="app.log", level=logging.INFO, filemode="w",
                    format=logformat, datefmt=datefmt)

parser = argparse.ArgumentParser()
parser.add_argument("--azure", "-az", help="Sizing for Azure", action='store_true')
parser.add_argument("--aws", "-a", help="Sizing for AWS", action='store_true')
parser.add_argument("--gcp", "-g", help="Sizing for GCP", action='store_true')
args = parser.parse_args()
separator = "--------------------------------------------------------------------"

stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(logging.Formatter(fmt=logformat, datefmt=datefmt))
logger = logging.getLogger("app")
logger.addHandler(stream_handler)

tenant = input('Customer Stack (api format, example api2): ')
cred = input('Customer Access Key/Secret (accesskey::secret format): ')
credsplit = cred.split("::")
accesskey = credsplit[0]
secret = credsplit[1]

def getToken():
	
	loginurl = "https://{}.prismacloud.io/login".format(tenant)

	credentials = {"username": accesskey,"password": secret}
	
	payload = json.dumps(credentials)
	headers = {
	    "Accept": "application/json; charset=UTF-8",
    	"Content-Type": "application/json; charset=UTF-8"
	}

	loginresp = requests.request("POST", loginurl, data=payload, headers=headers)
	if loginresp.status_code == 200:
		loginresp = json.loads(loginresp.text)
		token = loginresp['token']
	else:
		print('Please, validate your credentials and/or your tenant. There is an error.')
	return token

def dspmSizing(api_list):
    csp_count = 0
    url = "https://{}.prismacloud.io/search/api/v1/config/download".format(tenant)
    token = getToken()
    headers = {
         'Content-Type': 'application/json; charset=UTF-8',
         'Accept': 'text/csv',
         "x-redlock-auth": token
         }
    for api in api_list:
            querystring = json.dumps({"query": "config from cloud.resource where api.name = '" + api + "' AND resource.status = Active"})
            response = requests.request("POST", url, headers=headers, data=querystring)
            lines = response.text.count('\n')
            print("%s: %s" % (api, lines))
            csp_count += lines
    print("%s\nTotal Resources: %s \n%s" % (separator,csp_count,separator))

api_mapping = {
        "aws": [
            "aws-elasticache-cache-clusters",
            "aws-rds-describe-db-instances",
            # "aws-rds-db-cluster",
            "aws-s3api-get-bucket-acl",
            "aws-dynamodb-describe-table",
            "aws-docdb-db-cluster",
            "aws-emr-instance",
            "aws-emr-describe-cluster",
            "aws-redshift-describe-clusters",
            # "aws-dax-cluster",
            # "aws-fsx-file-system",
            "aws-efs-describe-file-systems",
            # "aws-es-describe-elasticsearch-domain"
        ],
        "azure": [
            "azure-storage-account-list",
            "azure-cosmos-db",
            "azure-database-maria-db-server",
            "azure-documentdb-cassandra-clusters",
            "azure-sql-db-list",
            "azure-sql-managed-instance",
            "azure-sql-server-list",
            "azure-cache-redis",
            "azure-mysql-flexible-server",
            "azure-postgres-flexible-server",
            "azure-synapse-workspace"
        ],
        "gcp": [
            'gcloud-filestore-instance',
            'gcloud-memorystore-memcached-instance',
            'gcloud-redis-instances-list',
            'gcloud-bigtable-instance-list',
            'gcloud-sql-instances-list',
            'gcloud-bigquery-dataset-list',
            'gcloud-storage-buckets-list',
            'gcloud-cloud-spanner-database'
        ]
}

if __name__ == '__main__':
    if args.aws == True:
        print("%s\nCalculating assests for AWS: \n%s" % (separator,separator))
        dspmSizing(api_mapping['aws'])
    elif args.azure == True:
        print("%s\nCalculating assests for Azure: \n%s" % (separator,separator))
        dspmSizing(api_mapping['azure'])  
    elif args.gcp == True:
        print("%s\nCalculating assests for GCP: \n%s" % (separator,separator))
        dspmSizing(api_mapping['gcp'])
    else:
        print("You must specify an argument.\n\x1B[3m'--aws'\x1B[0m for AWS\n\x1B[3m'--azure'\x1B[0m for Azure\n\x1B[3m'--gcp'\x1B[0m for GCP")