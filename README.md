# Prisma Cloud License Sizing Script

## TODO

- AWS: 
    - It only works for a single account, not for Organization yet. It must be execute by AWS Account.
- GCP:
    - It only works for a single project, not for Organization yet. You must specify the ProjectID.
- OCI:
    - It only works for the OCI tenant for Home Region. Not for OKE nodes yet.

## Overview

This document describes how to prepare for, and how to run the Prisma Cloud License Sizing Script for AWS, Azure, GCP, and OCI.

## Running the Script from Cloud Shell

1. Start a Cloud Shell session from the CSP UI, which should have the CLI tool, your credentials, ```git``` and ``jq`` already prepared
2. Clone this repository, e.g. ```git clone https://github.com/davidaavilar/pcs-sizing.git```
3. ```cd pcs-sizing```
4. ```pip install -r requeriments.txt```
- ```python3 pcs-sizing.py --aws``` for AWS.
- ```python3 pcs-sizing.py --azure``` for Azure.
- ```python3 pcs-sizing.py --gcp --project <GCP_PROJECT>``` for GCP.
- ```python3 pcs-sizing.py --oci``` for OCI.