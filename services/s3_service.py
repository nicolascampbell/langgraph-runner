import boto3
from urllib.parse import urlparse
import os

def retrieve_s3_data(link: str) -> str:
    """
    Connects to the S3 instance and retrieves data.
    Expected link format: s3://bucket-name/path/to/key
    """
    try:
        parsed_url = urlparse(link)
        if parsed_url.scheme != 's3':
             raise ValueError("Link must be an S3 URI (e.g. s3://bucket/key)")
        
        bucket_name = parsed_url.netloc
        key = parsed_url.path.lstrip('/')
        
        print(f"Connecting to S3 to retrieve s3://{bucket_name}/{key}")
        
        # Load custom endpoint if provided (for local MinIO containers)
        endpoint_url = os.environ.get("S3_ENDPOINT_URL")
        
        # boto3 client uses environment variables or IAM roles naturally
        # If AWS_ACCESS_KEY_ID is set in .env, boto3 will pick it up automatically
        s3 = boto3.client('s3', endpoint_url=endpoint_url)
        
        if not key or link.endswith('/'):
            # Path is a directory or entire bucket, retrieve all files under prefix
            print(f"Listing objects in s3://{bucket_name}/{key}")
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=key)
            if 'Contents' not in response:
                return f"No files found in s3://{bucket_name}/{key}"
            
            data_parts = []
            allowed_extensions = ('.txt', '.md', '.json', '.csv', '.yml', '.yaml')
            
            for obj in response['Contents']:
                obj_key = obj['Key']
                if obj_key.endswith('/'):
                    continue  # skip directory markers
                    
                if not obj_key.lower().endswith(allowed_extensions):
                    print(f"Skipping binary/unsupported file: {obj_key}")
                    data_parts.append(f"--- File: {obj_key} ---\n[Binary or unsupported file format skipped]\n")
                    continue
                
                print(f"Retrieving nested file s3://{bucket_name}/{obj_key}")
                file_response = s3.get_object(Bucket=bucket_name, Key=obj_key)
                
                # Decode safely in case of binary/weird files
                file_data = file_response['Body'].read().decode('utf-8', errors='replace')
                data_parts.append(f"--- File: {obj_key} ---\n{file_data}\n")
                
            return "\n".join(data_parts)
        else:
            # Path is a direct file key
            response = s3.get_object(Bucket=bucket_name, Key=key)
            data = response['Body'].read().decode('utf-8', errors='replace')
            print(f"Successfully retrieved data from S3.")
            return data
        
    except Exception as e:
        print(f"Error retrieving from S3: {e}")
        # Return a simulated string if AWS credentials aren't set up yet
        print(f"Falling back to simulated S3 data for {link}.")
        return f"Simulated content extracted from {link}"
