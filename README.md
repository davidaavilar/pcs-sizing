# Cortex Cloud Sizing Script

This script helps collect the necessary information to properly **size a Cortex Cloud project**. It automates the gathering of key metrics used to estimate resource consumption and licensing needs.

## What does this script collect?

The script scans cloud or hybrid environments to identify resources in the following categories:

| Resource Type                        | Unit Equivalent               |
|--------------------------------------|-------------------------------|
| VMs not running containers           | 1 VM                          |
| VMs running containers               | 1 VM                          |
| CaaS                                 | 10 Managed Containers         |
| Serverless Functions                 | 25 Serverless Functions       |
| Cloud Buckets                        | 10 Cloud Buckets              |
| Managed Cloud Database (PaaS)        | 2 PaaS Databases              |
| DBaaS TB stored                      | 1 TB Stored                   |
| SaaS users                           | 10 SaaS Users                 |
| Cloud ASM - service                  | 4 Unmanaged Assets            |

## Purpose

The collected data is used to estimate the capacity and licensing model required to deploy **Cortex Cloud**, making it easier to plan architecture and procurement.

## Requirements

- Python 3.x
- Access to the cloud resources to be analyzed (read-only permissions are sufficient in most cases)

## GCP APIs Requirements

- Cloud Functions API
- Compute Engine API
- Kubernetes Engine API
- Cloud Run Admin API
- Cloud Bigtable Admin API
- Cloud Bigtable API
- Cloud Resource Manager API
- Cloud Storage API
- BigQuery API

## Running the Script from Cloud Shell

1. Start a Cloud Shell session from the CSP UI, which should have the CLI tool, your credentials, ```git``` and ``jq`` already prepared
2. Clone this repository, e.g. ```git clone https://github.com/davidaavilar/pcs-sizing.git```
3. ```cd pcs-sizing```
4. ```pip install -r requirements.txt```
- ```python3 cc-sizing.py --aws --region us``` eg. region prefix us, eu, ap
- ```python3 cc-sizing.py --azure```
- ```python3 cc-sizing.py --gcp```
- ```python3 cc-sizing.py --oci```

## TODO

DBaaS TB stored, SaaS users and Cloud ASM aren't ready.

---
