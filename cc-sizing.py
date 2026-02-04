import json, os, argparse, math
import boto3, botocore
from botocore.exceptions import ClientError

parser = argparse.ArgumentParser()
parser.add_argument("--azure", "-az", help="Sizing for Azure", action='store_true')
parser.add_argument("--aws", "-a", help="Sizing for AWS", action='store_true')
parser.add_argument("--gcp", "-g", help="Sizing for GCP", action='store_true')
parser.add_argument("--oci", "-o", help="Sizing for OCI", action='store_true')
parser.add_argument("--region-prefix", "-rp", help="Filter AWS regions by prefix (e.g. us, eu, ap)", default=None)
args = parser.parse_args()
separator = "-"*140

cc_metering = {
    "serverless": 25,
    "vm": 1,
    "caas": 10,
    "buckets": 10,
    "db": 2,
    "saas_users": 10,
    "asm": 4
}

cc_metering_table = [
    ["VMs not running containers", "1 VM"],
    ["VMs running containers", "1 VM"],
    ["CaaS", "10 Managed Containers"],
    ["Serverless Functions", "25 Serverless Functions"],
    ["Cloud Buckets", "10 Cloud Buckets"],
    ["Managed Cloud Database (PaaS)", "2 PaaS Databases"],
    ["DBaaS TB stored", "1 TB Stored"],
    ["SaaS users", "10 SaaS Users"],
    ["Cloud ASM - service", "4 Unmanaged Assets"]
]

def cortex_cloud_metering():
    print(f"\n{separator}\nCortex Cloud Workload Metering\n{separator}")
    tables(None, cc_metering_table)

def tables(account_info, data):
    print(f"{'Account':<50} {'Service':<40} {'Count':<10}\n{separator}")
    account = f'{account_info["Id"]} ({account_info["Name"]})' if account_info else ""
    for a, b in data:
        print(f"{account:<50} {a:<40} {b:<10}")
    print(separator)

def licensing_count(cloud, vm, serverless, caas, buckets, db):
    total = (
        math.ceil(vm / cc_metering["vm"]) +
        math.ceil(serverless / cc_metering["serverless"]) +
        math.ceil(caas / cc_metering["caas"]) +
        math.ceil(buckets / cc_metering["buckets"]) +
        math.ceil(db / cc_metering["db"])
    )

    c1 = (
        math.ceil(buckets / cc_metering["buckets"]) +
        math.ceil(db / cc_metering["db"])
    )

    c3 = (
        math.ceil(vm / cc_metering["vm"]) +
        math.ceil(serverless / cc_metering["serverless"]) +
        math.ceil(caas / cc_metering["caas"])
    )

    print(f"Total C1 (Buckets,DBS) Cortex Cloud workloads (SKU) to cover this {cloud} Account: **({c1})**\n")
    print(f"Total C3 (Compute Workloaks) Cortex Cloud workloads (SKU) to cover this {cloud} Account (if needed): **({c3})**\n")
    print(f"Total Cortex Cloud workloads (SKU) to cover this {cloud} Account: **({total})** \n{separator}")


# ---------------------------- AWS ----------------------------
def aws(account, session=None):
    if session is None:
        session = boto3.Session()

    try:
        regions = [r['RegionName'] for r in session.client('ec2').describe_regions()['Regions']]
        if args.region_prefix:
            regions = [r for r in regions if r.startswith(args.region_prefix)]
    except botocore.exceptions.ClientError as error:
        raise error

    ec2_all = eks_all = fargate_all = lambdas_all = rds_all = dynamodb_all = efs_all = 0

    # ---------------- S3 Buckets (global) ----------------
    try:
        s3 = session.client('s3')
        s3_all = len(s3.list_buckets()['Buckets'])
    except botocore.exceptions.ClientError as error:
        s3_all = 0
        print(f"S3 error: {error}")

    # ---------------- Regional Services ----------------
    for region in regions:

        # EC2 Running 

        try:
            ec2 = session.client('ec2', region_name=region)
            ec2_group = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-code', 'Values': ["16"]}]
            )['Reservations']
            ec2_all += sum(len(r['Instances']) for r in ec2_group)
        except botocore.exceptions.ClientError as error:
            raise error

        # EC2 Running but are EKS nodes
        try:
            for ec2_item in ec2_group:
                tags = ec2_item['Instances'][0].get('Tags', [])
                if any("eks:" in tag["Key"] for tag in tags):
                    eks_all += 1
        except botocore.exceptions.ClientError as error:
            raise error

        # Fargate Task Definitions
        try:
            ecs_client = session.client('ecs', region_name=region)
            fargate_all += len(ecs_client.list_task_definitions()['taskDefinitionArns'])
        except botocore.exceptions.ClientError as error:
            raise error

        # Fargate Task Definitions
        try:
            lambda_client = session.client('lambda', region_name=region)
            lambdas_all += len(lambda_client.list_functions()['Functions'])
        except botocore.exceptions.ClientError as error:
            raise error
        
        # RDS instances
        try:
            rds = session.client('rds', region_name=region)
            rds_all += len(rds.describe_db_instances()['DBInstances'])
        except botocore.exceptions.ClientError as error:
            raise error

        # DynamoDB
        try:
            dynamodb = session.client('dynamodb', region_name=region)
            dynamodb_all += len(dynamodb.list_tables()['TableNames'])
        except botocore.exceptions.ClientError as error:
            raise error

        # EFS
        try:
            efs = session.client('efs', region_name=region)
            efs_all += len(efs.describe_file_systems()['FileSystems'])
        except botocore.exceptions.ClientError as error:
            raise error

    tables(account, [
        ["EC2 Instances", ec2_all-eks_all],
        ["EKS Nodes", eks_all],
        ["Fargate_Tasks", fargate_all],
        ["Lambdas", lambdas_all],
        ["S3_Buckets", s3_all],   
        ["RDS Instances", rds_all],
        ["DynamoDB Tables", dynamodb_all],
        ["EFS Systems", efs_all]
    ])
    licensing_count("AWS", ec2_all+eks_all, lambdas_all, fargate_all, s3_all, rds_all+dynamodb_all+efs_all)

def pcs_sizing_aws():
    sts = boto3.client("sts")
    iam = boto3.client('iam')
    org = boto3.client('organizations')
    accounts = []

    aliases = iam.list_account_aliases().get('AccountAliases', [])
    account_info = {
        "Name": aliases[0] if aliases else 'No alias',
        "Id": sts.get_caller_identity()["Account"]
    }
    aws(account_info)

    try:
        paginator = org.get_paginator('list_accounts')
        for page in paginator.paginate():
            for acct in page['Accounts']:
                if acct['Status'] == "ACTIVE":
                    accounts.append(acct)
    except botocore.exceptions.ClientError as error:
        print(f"{error}\n{separator}")

    for account in accounts:
        role_arn = f"arn:aws:iam::{account['Id']}:role/OrganizationAccountAccessRole"
        try:
            creds = boto3.client('sts').assume_role(
                RoleArn=role_arn, RoleSessionName='CrossAccountSession'
            )['Credentials']
            session = boto3.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken']
            )
            aws({"Name": account['Name'], "Id": account['Id']}, session=session)
        except botocore.exceptions.ClientError as error:
            print(f"Error with {account['Name']} - {account['Id']}:\n{error}\n{separator}")
            continue

# ---------------------------- Azure ----------------------------
def pcs_sizing_az():
    from azure.mgmt.compute import ComputeManagementClient
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.containerservice import ContainerServiceClient
    from azure.mgmt.subscription import SubscriptionClient
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.cosmosdb import CosmosDBManagementClient
    from azure.mgmt.storage import StorageManagementClient
    from azure.mgmt.core.tools import parse_resource_id

    sub_client = SubscriptionClient(DefaultAzureCredential())
    print(f"\n{separator}\nGetting Resources from AZURE\n{separator}")
    for sub in sub_client.subscriptions.list():
        compute_client = ComputeManagementClient(DefaultAzureCredential(), sub.subscription_id)
        containerservice_client = ContainerServiceClient(DefaultAzureCredential(), sub.subscription_id)
        app_service_client = WebSiteManagementClient(DefaultAzureCredential(), sub.subscription_id)
        sql_client = SqlManagementClient(DefaultAzureCredential(), sub.subscription_id)
        cosmos_client = CosmosDBManagementClient(DefaultAzureCredential(), sub.subscription_id)
        storage_client = StorageManagementClient(DefaultAzureCredential(), sub.subscription_id)

        # VMs
        vm_list = [vm.name for vm in compute_client.virtual_machines.list_all()
                   if compute_client.virtual_machines.instance_view(vm.id.split('/')[4], vm.name).statuses[1].code == 'PowerState/running']

        # AKS Nodes
        node_count = sum(ap.count for cl in containerservice_client.managed_clusters.list()
                         for ap in containerservice_client.agent_pools.list(cl.id.split('/')[4], cl.name))

        # Functions
        function_list = sum(1 for f in app_service_client.web_apps.list() if f.kind.startswith('function'))

        # SQL
        sql_db_count = sum(
            sum(1 for db in sql_client.databases.list_by_server(parse_resource_id(s.id)['resource_group'], s.name)
        if db.name.lower() != 'master')
        for s in sql_client.servers.list()
        )

        # Cosmos DB
        cosmos_count = sum(1 for acc in cosmos_client.database_accounts.list() if acc.public_network_access=="Enabled")

        # Storage
        storage_count = sum(1 for _ in storage_client.storage_accounts.list())

        account_info = {"Name": sub.display_name, "Id": sub.subscription_id}
        tables(account_info, [
            ["VM", len(vm_list)],
            ["AKS_NODES", node_count],
            ["AZURE_FUNCTIONS", function_list],
            ["AZURE_SQL", sql_db_count],
            ["COSMO_DB", cosmos_count],
            ["STORAGE_ACCOUNTS", storage_count]
        ])
        licensing_count("Azure", len(vm_list)+node_count, function_list, 0, storage_count, cosmos_count+sql_db_count)

# ---------------------------- GCP ----------------------------
def pcs_sizing_gcp():
    import google.auth
    from google.cloud import compute_v1, container_v1beta1, functions_v1, bigquery, bigtable, storage
    from googleapiclient.discovery import build
    from collections import defaultdict

    print(f"\n{separator}\nGetting Resources from GCP\n{separator}")
    service = build('cloudresourcemanager', 'v1')
    request = service.projects().list()
    projects = []

    while request:
        response = request.execute()
        for project in response.get("projects", []):
            projects.append({"projectId": project["projectId"], "name": project.get("name",""), "lifecycleState": project.get("lifecycleState","")})
        request = service.projects().list_next(previous_request=request, previous_response=response)

    for p in projects:
        if p['lifecycleState'] != "ACTIVE":
            continue
        project_id = p['projectId']
        project_name = p['name']

        # Compute Instances
        compute_list = [i.name for zone, resp in compute_v1.InstancesClient().aggregated_list(
            compute_v1.AggregatedListInstancesRequest(project=project_id)) if resp.instances for i in resp.instances if i.status=="RUNNING"]

        # GKE Nodes
        gke_client = container_v1beta1.ClusterManagerClient()
        node_count = sum(c.current_node_count for c in gke_client.list_clusters(container_v1beta1.ListClustersRequest(project_id=project_id, zone="-")).clusters)

        # Functions
        gcp_functions = [fn.name for fn in functions_v1.CloudFunctionsServiceClient().list_functions(request={"parent": f"projects/{project_id}/locations/-"})]

        # CloudRun
        cloudrun = build("run", "v1")
        gcp_cloudRun = [s["metadata"]["name"] for s in cloudrun.projects().locations().services().list(parent=f"projects/{project_id}/locations/-").execute().get("items", [])]

        # Buckets
        gcp_buckets = [b.name for b in storage.Client(project=project_id).list_buckets()]

        # BigQuery
        gcp_bigquery_ds = [ds.dataset_id for ds in bigquery.Client(project=project_id).list_datasets()]

        # Bigtable
        try:
            bt_client = bigtable.Client(project=project_id, admin=True)
            instances, failed_locations = bt_client.list_instances()
            gcp_bigtables = [inst.instance_id for inst in instances]
        except Exception as e:
            print(f"[SKIP] Bigtable {project_id}: {e}")
            gcp_bigtables = []

        # Cloud SQL
        sqladmin = build("sqladmin", "v1beta4")
        gcp_cloudsql = [i["name"] for i in sqladmin.instances().list(project=project_id).execute().get("items", []) if i["state"]=="RUNNABLE"]

        account_info = {"Name": project_name, "Id": project_id}
        tables(account_info, [
            ["Compute Instances", len(compute_list)],
            ["GKE Nodes", node_count],
            ["Google Functions", len(gcp_functions)],
            ["Google CloudRun", len(gcp_cloudRun)],
            ["Cloud Storages", len(gcp_buckets)],
            ["BigQuery Datasets", len(gcp_bigquery_ds)],
            ["BigTable instances", len(gcp_bigtables)],
            ["CloudSQL instances", len(gcp_cloudsql)]
        ])
        licensing_count("GCP", len(compute_list)+node_count, len(gcp_functions)+len(gcp_cloudRun), 0, len(gcp_buckets), len(gcp_bigquery_ds)+len(gcp_bigtables)+len(gcp_cloudsql))

# ---------------------------- OCI ----------------------------
def pcs_sizing_oci():
    import oci
    print(f"\n{separator}\nGetting Resources from OCI\n{separator}")
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)
    compute = oci.core.ComputeClient(config)

    compartments = identity.list_compartments(compartment_id=config['tenancy']).data
    compartments_list = [{"Name":"root","Id":config['tenancy']}] + [{"Name":c.name,"Id":c.id} for c in compartments]

    for comp in compartments_list:
        compute_count = sum(1 for i in compute.list_instances(compartment_id=comp['Id']).data if i.lifecycle_state=="RUNNING")
        tables({"Name": comp['Name'], "Id": comp['Id']}, [["Compute_Instances", compute_count]])

# ---------------------------- MAIN ----------------------------
if __name__ == '__main__':
    if args.aws:
        pcs_sizing_aws()
    elif args.azure:
        pcs_sizing_az()
    elif args.oci:
        pcs_sizing_oci()
    elif args.gcp:
        pcs_sizing_gcp()
    else:
        print("You must specify an argument:\n--aws | --azure | --gcp | --oci")
