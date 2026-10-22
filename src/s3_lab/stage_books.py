#!/usr/bin/env python3
"""
Stage books from Project Gutenberg into an S3 bucket and make it public.
"""

import json
import logging
import os
import sys
import time
import boto3
from botocore.exceptions import ClientError
import requests

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Shared S3 client at module level
s3 = boto3.client("s3", region_name="us-east-1")


def parse_args():
    """Read command line arguments: list file, index path, and bucket name."""
    if len(sys.argv) < 4:
        print("Usage: python stage_books.py <book_list> <index_path> <bucket_name>")
        sys.exit(1)
    return sys.argv[1], sys.argv[2], sys.argv[3]


def download_books(list_file, dest_dir="books"):
    """Download books from URLs listed in list_file."""
    os.makedirs(dest_dir, exist_ok=True)
    file_paths = []

    with open(list_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        filename = url.split("/")[-1]
        dest_path = os.path.join(dest_dir, filename)
        file_paths.append(dest_path)

        if os.path.exists(dest_path):
            continue

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(response.content)
            time.sleep(1)
        except requests.RequestException as e:
            log.error(f"Error downloading {url}: {e}")

    return file_paths


def create_bucket(bucket):
    """Create the S3 bucket if it doesn't already exist."""
    try:
        s3.head_bucket(Bucket=bucket)
        log.info(f"Bucket '{bucket}' already exists.")
        return True
    except ClientError:
        try:
            s3.create_bucket(Bucket=bucket)
            log.info(f"Created bucket '{bucket}'.")
            return True
        except ClientError as e:
            log.error(f"Error creating bucket: {e}")
            return False


def make_public(bucket):
    """Turn off block public access and attach a public read policy."""
    try:
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
        )
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*"
            }]
        }
        s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        log.info(f"Bucket '{bucket}' is now public.")
        return True
    except ClientError as e:
        log.error(f"Error making bucket public: {e}")
        return False


def upload_files(bucket, file_paths):
    """Upload all downloaded books to the bucket."""
    count = 0
    for path in file_paths:
        if not os.path.exists(path):
            continue
        key = os.path.basename(path)
        try:
            s3.upload_file(path, bucket, key, ExtraArgs={"ContentType": "text/plain; charset=utf-8"})
            count += 1
        except ClientError as e:
            log.error(f"Error uploading {key}: {e}")
    return count


def upload_index(bucket, index_path):
    """Upload the index.html page."""
    try:
        s3.upload_file(index_path, bucket, "index.html", ExtraArgs={"ContentType": "text/html"})
        log.info("Uploaded index.html successfully.")
        return True
    except ClientError as e:
        log.error(f"Error uploading index.html: {e}")
        return False


def main():
    list_file, index_path, bucket = parse_args()

    file_paths = download_books(list_file)
    if not file_paths:
        sys.exit(1)

    if not create_bucket(bucket):
        sys.exit(1)

    if not make_public(bucket):
        sys.exit(1)

    uploaded = upload_files(bucket, file_paths)
    log.info(f"Successfully uploaded {uploaded} books.")

    if not upload_index(bucket, index_path):
        sys.exit(1)

    log.info(f"Task 1 complete! URL: https://{bucket}.s3.amazonaws.com/index.html")


if __name__ == "__main__":
    main()
