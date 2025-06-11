import json, os, argparse, math

parser = argparse.ArgumentParser()
parser.add_argument("--azure", "-az", help="Sizing for Azure", action='store_true')
parser.add_argument("--aws", "-a", help="Sizing for AWS", action='store_true')
parser.add_argument("--gcp", "-g", help="Sizing for GCP", action='store_true')
parser.add_argument("--oci", "-o", help="Sizing for OCI", action='store_true')
parser.add_argument("--project", "-p", help="Project (only for GCP)", type=str)
args = parser.parse_args()
separator = "-----------------------------------------------------------------------------------------------------"

regions_preffix = "us"

cc_metering = {"serverless": 25, 
               "vm": 1,
               "caas": 10,
               "buckets": 10,
               "db": 2,
               "saas_users": 10,
               "asm": 4}

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
    print("\n{}\n{}\n{}".format(separator,"Cortex Cloud Workload Metering",separator))
    tables(None,"",cc_metering_table)
    
def tables(account,acc,data):
    for i in data:
        a,b = i
        if account == None:
            print ("{:<0} {:<40} {:<10}".format(acc,a,b))
        else:
            print ("{:<50} {:<40} {:<10}".format(acc,a,b))
    print(separator)

def pcs_sizing_aws():
    import boto3
    import botocore
    from botocore.exceptions import ClientError

    client_ec2 = boto3.client('ec2')
    sts = boto3.client("sts")
    org = boto3.client('organizations')
    iam = boto3.client('iam')

    print("\n{}\nGetting Resources from AWS for {} Regions\n{}".format(separator,regions_preffix.upper(), separator))

    accounts = []
    # paginator = org.get_paginator('list_accounts')
    # for page in paginator.paginate():
    #     for account in page['Accounts']:
    #         accounts.append(account['Id'])
    #         response = sts.assume_role(
    #             RoleArn="arn:aws:iam::" + account['Id'] + ":role/OrganizationAccountAccessRole",
    #             RoleSessionName=account['Id']
    #         )
    try:
        accountid = sts.get_caller_identity()["Account"]
        aliases = iam.list_account_aliases()['AccountAliases']
        account_name = aliases[0] if aliases else 'No alias found'
        account = f"{accountid} ({account_name})"
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error

    try:
        regions = [region['RegionName'] for region in client_ec2.describe_regions()['Regions']]
    except botocore.exceptions.ClientError as error:
        raise error
    
    regions = [x for x in regions if x.startswith(regions_preffix)]

    try:
        ec2_all = 0
        eks_all = 0
        fargate_all = 0
        lambdas_all = 0
        rds_all = 0
        dynamodb_all = 0
        s3_all = 0
        redshift_all = 0
        efs_all = 0

        for region in regions:
            # Get EC2 instances running.
            try:
                ec2 = boto3.client('ec2',region_name=region)
                ec2_group = ec2.describe_instances(
                    Filters=[{
                    'Name': 'instance-state-code',
                    'Values': ["16"] # 0 (pending), 16 (running), 32 (shutting-down), 48 (terminated), 64 (stopping), and 80 (stopped)
                        },
                    ]
                    )['Reservations']
                ec2_all += len(ec2_group)
            except botocore.exceptions.ClientError as error:
                raise error
    
            try:
            # Get EC2 instances running on EKS.
                client_ecs = boto3.client('ecs',region_name=region)
                eks_list = []
                for ec2 in ec2_group:
                    tags = ec2['Instances'][0]['Tags']
                    for tag in tags:
                        if "eks:" in tag["Key"]:
                            eks_list.append(ec2['Instances'][0])
                            eks_all += 1
                            break
            except botocore.exceptions.ClientError as error:
                raise error
            
            try:
                # Get Fargate task running.
                fargate_tasks = client_ecs.list_task_definitions()['taskDefinitionArns']
                fargate_all += len(fargate_tasks)
            except botocore.exceptions.ClientError as error:
                raise error
            
            try:
            # Get AWS Lambdas
                lambda_client = boto3.client('lambda',region_name=region)
                lambdas = lambda_client.list_functions()['Functions']
                lambdas_all += len(lambdas)
            except botocore.exceptions.ClientError as error:
                raise error
            
            try:
                # Get S3
                s3 = boto3.client('s3')
                buckets = s3.list_buckets()['Buckets']
                s3_all += len(buckets)
            except botocore.exceptions.ClientError as error:
                raise error

            try:
                # Get RDS Instances
                rds = boto3.client('rds')
                instances = rds.describe_db_instances()['DBInstances']
                rds_all += len(instances)
            except botocore.exceptions.ClientError as error:
                raise error
                        
            try:
                # Get DynamoDB
                dynamodb = boto3.client('dynamodb')
                dynamo_tables = dynamodb.list_tables()['TableNames']
                dynamodb_all += len(dynamo_tables)
            except botocore.exceptions.ClientError as error:
                raise error

            try:
                # Get Redshift
                redshift = boto3.client('redshift')
                clusters = redshift.describe_clusters()['Clusters']
                redshift_all += len(clusters)
            except botocore.exceptions.ClientError as error:
                raise error
            
            try:
                # Get EFS
                efs = boto3.client('efs')
                file_systems = efs.describe_file_systems()['FileSystems']
                efs_all = len(file_systems)
            except botocore.exceptions.ClientError as error:
                raise error

        print ("{:<50} {:<40} {:<10}\n{}".format('Account','Service','Count',separator))

        tables("Account",account,
            [
            ["EC2 Instances", ec2_all-eks_all],
            ["EKS Nodes", eks_all],
            ["Fargate_Tasks", fargate_all],
            ["Lambdas", lambdas_all],
            ["S3_Buckets", s3_all],
            ["Redshift Clusters", redshift_all],
            ["RDS Instances", rds_all],
            ["DynamoDB Tables", dynamodb_all],
            ["EFS Systems", efs_all]
            ])
        
        #Licensing Sum
        aws_licensing_count = (
            math.ceil(ec2_all-eks_all / cc_metering["vm"]) +
            math.ceil(lambdas_all / cc_metering["serverless"]) +
            math.ceil(fargate_all / cc_metering["caas"]) +
            math.ceil(s3_all / cc_metering["buckets"]) +
            math.ceil((redshift_all + rds_all + dynamodb_all + efs_all) / cc_metering["db"])
        )
        print("You will need {} Cortex Cloud workloads (SKU) to cover this AWS Account".format(aws_licensing_count))
        
    except botocore.exceptions.ClientError as error:
        raise error

def pcs_sizing_az():

    from azure.mgmt.compute import ComputeManagementClient
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.containerservice import ContainerServiceClient
    from azure.mgmt.subscription import SubscriptionClient
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.cosmosdb import CosmosDBManagementClient
    from azure.mgmt.storage import StorageManagementClient


    sub_client = SubscriptionClient(credential=DefaultAzureCredential())
    print("\n{}\nGetting Resources from AZURE\n{}".format(separator,separator))
    for sub in sub_client.subscriptions.list():
        compute_client = ComputeManagementClient(credential=DefaultAzureCredential(), subscription_id=sub.subscription_id)
        containerservice_client = ContainerServiceClient(credential=DefaultAzureCredential(), subscription_id=sub.subscription_id)
        app_service_client = WebSiteManagementClient(credential=DefaultAzureCredential(), subscription_id=sub.subscription_id)
        sql_client = SqlManagementClient(credential=DefaultAzureCredential(), subscription_id=sub.subscription_id)
        cosmos_client = CosmosDBManagementClient(credential=DefaultAzureCredential(), subscription_id=sub.subscription_id)
        storage_client = StorageManagementClient(credential=DefaultAzureCredential(), subscription_id=sub.subscription_id)

        # List VMs in subscription
        vm_list = []
        for vm in compute_client.virtual_machines.list_all():
            array = vm.id.split("/")
            resource_group = array[4]
            vm_name = array[-1]
            statuses = compute_client.virtual_machines.instance_view(resource_group, vm_name).statuses
            status = len(statuses) >= 2 and statuses[1]
            if status and status.code == 'PowerState/running':
                vm_list.append(vm_name)

        # List AKS Clusters in subscription

        clusters_list = []
        node_count = 0
        for cl in containerservice_client.managed_clusters.list():
            clusters_list.append(cl.name)
            agent_pool = containerservice_client.agent_pools.list(
                cl.id.split('/')[4].strip(),
                cl.name
            )
            for ap in agent_pool:
                node_count += ap.count

        # List Azure Functions
        function_list = 0
        for function in app_service_client.web_apps.list():
            if function.kind.startswith('function'):
                function_list += 1

        # List Azure SQL
        sql_db_count = 0
        for server in sql_client.servers.list():
            for db in sql_client.databases.list_by_server(server.resource_group_name, server.name):
                sql_db_count += 1

        # List Cosmo DB
        cosmos_count = 0
        for account in cosmos_client.database_accounts.list():
            cosmos_count += 1 if account.public_network_access == "Enabled" else None

        # List Storage Accounts
        storage_count = 0
        for account in storage_client.storage_accounts.list():
            storage_count += 1

        print ("{:<50} {:<40} {:<10}\n{}".format('Subscription','Service','Count',separator))
        tables("Subscription",str(sub.display_name + " (" + sub.subscription_id.split('-')[4].strip() + ")"),
            [
            ["VM", len(vm_list)],
            ["AKS_NODES", node_count],
            ["AZURE_FUNCTIONS",function_list],
            ["AZURE_SQL", sql_db_count],
            ["COSMO_DB", cosmos_count],
            ["STORAGE_ACCOUNTS", storage_count]
            ])
        
        #Licensing Sum
        az_licensing_count = (
            math.ceil(len(vm_list)+node_count / cc_metering["vm"]) +
            math.ceil(function_list / cc_metering["serverless"]) +
            math.ceil(storage_count / cc_metering["buckets"]) +
            math.ceil((cosmos_count + sql_db_count) / cc_metering["db"])
        )
        print("You will need {} Cortex Cloud workloads (SKU) to cover this Azure Subscription\n{}".format(az_licensing_count,separator))

def pcs_sizing_gcp(project):

    import google.auth
    from google.auth import compute_engine
    from google.cloud.resourcemanager import ProjectsClient
    from google.cloud import compute_v1
    from google.cloud import container_v1beta1
    from google.cloud import functions_v1
    from google.cloud import bigquery
    from google.cloud import bigtable
    from google.cloud import storage
    from google.cloud import resourcemanager_v3
    from googleapiclient.discovery import build
    from collections import defaultdict
    
    print("\n{}\nGetting Resources from GCP\n{}".format(separator,separator))

    # pj_client = resourcemanager_v3.ProjectsClient()
    # request = resourcemanager_v3.ListProjectsRequest(
    #     parent="parent_value",
    # )
    # page_result = pj_client.list_projects()
    # for response in page_result:
    #     print(response)

    # Getting the Compute Instances
    compute_client = compute_v1.InstancesClient()
    request = compute_v1.AggregatedListInstancesRequest()
    request.project = project
    agg_list = compute_client.aggregated_list(request=request)
    all_instances = defaultdict(list)
    compute_list = []
    for zone, response in agg_list:
        if response.instances:
            for instance in response.instances:
                if instance.status == "RUNNING":
                    compute_list.append(instance.name)

    # Getting the Compute Instances for GKE
    gke_client = container_v1beta1.ClusterManagerClient()
    gke_request = container_v1beta1.ListClustersRequest()
    gke_request.project_id = project
    gke_request.zone = "-"
    response = gke_client.list_clusters(request=gke_request)
    node_count = 0
    for cluster in response.clusters:
        node_count += cluster.current_node_count

    ### Get Google Functions (Run)
    client = functions_v1.CloudFunctionsServiceClient()
    parent = f"projects/{project}/locations/-"
    functions = client.list_functions(request={"parent": parent})
    gcp_functions = [fn.name for fn in functions]

    client = build("run", "v1")
    parent = f"projects/{project}/locations/-"
    response = client.projects().locations().services().list(parent=parent).execute()
    gcp_cloudRun = [s["metadata"]["name"] for s in response.get("items", [])]

    ### Get Cloud Storage buckets
    client = storage.Client(project=project)
    buckets = client.list_buckets()
    gcp_buckets = [bucket.name for bucket in buckets]

    ## Get BigQuery datasets
    client = bigquery.Client(project=project)
    datasets = client.list_datasets()
    gcp_bigquery_ds = [ds.dataset_id for ds in datasets]

    ### Get Bigtable instances

    client = bigtable.Client(project=project, admin=True)
    instances, _ = client.list_instances()
    gcp_bigtables = [instance.instance_id for instance in instances]

    ### Get Cloud SQL instances
    sqladmin = build("sqladmin", "v1beta4")
    response = sqladmin.instances().list(project=project).execute()
    if "items" in response:
        gcp_cloudql = [instance["name"] for instance in response["items"] if instance["state"] == "RUNNABLE"]
    else:
        gcp_cloudql = []
    
    print ("{:<50} {:<40} {:<10}\n{}".format('Project','Service','Count',separator))
    tables("Project",project,
           [
        ["Compute Instances", len(compute_list)],
        ["GKE Nodes", node_count],
        ["Google Functions", len(gcp_functions)],
        ["Google CloudRun", len(gcp_cloudRun)],
        ["Cloud Storages", len(gcp_buckets)],
        ["BigQuery Datasets", len(gcp_bigquery_ds)],
        ["BigTable instances", len(gcp_bigtables)],
        ["CloudSQL instances", len(gcp_cloudql)],
        ])

def pcs_sizing_oci():

    import oci
    
    print("\n{}\nGetting Resources from OCI\n{}".format(separator,separator))
    config = oci.config.from_file()
    IdentityClient = oci.identity.IdentityClient(config)
    ComputeClient = oci.core.ComputeClient(config)
    ContainerClient = oci.container_engine.ContainerEngineClient(config)

    # List all Compartments

    compartments = IdentityClient.list_compartments(
        compartment_id=config['tenancy']
    )
    
    # Adding the compartment root to the list
    compartments_list = []
    compartments_list.append({'Name':"root","Id":config['tenancy']})

    for compartment in compartments.data:
        data = {'Name':compartment.name,"Id":compartment.id}
        compartments_list.append(data)

    # For every compartment, list all the VMs and OKE nodes (TODO)
    
    print ("{:<40} {:<20} {:<10}\n{}".format('Compartment','Service','Count',separator))
    for compartment in compartments_list:
        response = ComputeClient.list_instances(compartment_id=compartment['Id'])
        compute_oci = 0
        for instance in response.data:
            if instance.lifecycle_state == "RUNNING":
                compute_oci += 1

        # node_pool = ContainerClient.list_node_pools(compartment_id=compartment['Id'])
        # print(node_pool.data)
    
        tables("Compartment",compartment['Name'],
            [
            ["Compute_Instances", compute_oci]
            ])
        
if __name__ == '__main__':
    # cortex_cloud_metering()
    if args.aws == True:
        pcs_sizing_aws()
    elif args.azure == True:
        pcs_sizing_az()  
    elif args.oci == True:
        pcs_sizing_oci()  
    elif args.gcp == True:#and args.project:
        pcs_sizing_gcp(project=args.project)
    elif args.gcp == True and not args.project:
        print("If GCP is selected, you must specify a project.")
        exit()
    else:
        print("You must specify an argument.\n\x1B[3m'--aws'\x1B[0m for AWS\n\x1B[3m'--azure'\x1B[0m for Azure\n\x1B[3m'--gcp --project <project-name>'\x1B[0m for GCP\n\x1B[3m'--oci'\x1B[0m for OCI")