#!/bin/bash

# Get today's date in YYYY-MM-DD format
DATE=$(date +%Y-%m-%d)

# Navigate to the options_data directory
cd options_data || exit

# Zip the folder's contents without the parent folder structure
zip -r "../${DATE}.zip" "${DATE}"/*

# Navigate back to the root directory
cd ..

aws configure list
# aws configure list --profile personal

# Upload the zip file to S3
aws s3 cp "./${DATE}.zip" "s3://project-x-data-1783/${DATE}.zip"
# aws s3 cp "./${DATE}.zip" "s3://project-x-data-183/${DATE}.zip" --profile personal

# Optional: Cleanup local zip file after successful upload
# rm "./${DATE}.zip"
